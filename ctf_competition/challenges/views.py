from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse
from django.utils.timezone import now, timedelta
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Question, Submission, PlayerScore, ChallengeTimer
import json
import time
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.views import LoginView



@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='not_started_page')
def set_timer(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start':
            try:
                hours = int(request.POST.get('hours', 0) or 0)
                minutes = int(request.POST.get('minutes', 0) or 0)
                seconds = int(request.POST.get('seconds', 0) or 0)
            except ValueError:
                return render(request, 'challenges/set_timer.html', {
                    'error': 'Please provide valid numbers for hours, minutes, and seconds.'
                })

            duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            ChallengeTimer.objects.all().delete()  # Ensure only one timer exists
            ChallengeTimer.objects.create(start_time=now(), duration=duration)
            messages.success(request, "Timer started successfully!")
            return redirect('set_timer')

        elif action == 'pause':
            timer = ChallengeTimer.objects.first()
            if timer and timer.is_active():
                timer.duration = timer.time_left()  # Update duration to remaining time
                timer.start_time = None  # Pause the timer
                timer.save()
                messages.success(request, "Timer paused successfully!")
            else:
                messages.error(request, "No active timer to pause.")
            return redirect('set_timer')

        elif action == 'reset':
            ChallengeTimer.objects.all().delete()  # Delete all timers
            messages.success(request, "Timer reset successfully!")
            return redirect('set_timer')

        elif action == 'resume':
            timer = ChallengeTimer.objects.first()
            if timer and timer.duration and not timer.start_time:
                timer.start_time = now()  # Resume the timer
                timer.save()
                messages.success(request, "Timer resumed successfully!")
            else:
                messages.error(request, "No paused timer to resume.")
            return redirect('set_timer')

    timer = ChallengeTimer.objects.first()
    return render(request, 'challenges/set_timer.html', {'timer': timer})


@login_required
def question_list(request):
    timer = ChallengeTimer.objects.first()

    # Redirect non-admin users if timer has not started
    if not request.user.is_staff and not request.user.is_superuser:
        if not timer or timer.start_time is None:
            return redirect('not_started_page')
        elif not timer.is_active() and timer.start_time is not None:
            return redirect('paused_page')
        elif timer.is_active() and timer.time_left().total_seconds() <= 0:
            return redirect('finished_page')

    questions = Question.objects.all()
    return render(request, 'challenges/questions.html', {'questions': questions})


@login_required
def submit_answer(request, question_id):
    
    timer = ChallengeTimer.objects.first()
    
    if not timer or not timer.is_active():
        if not timer:
            return redirect('not_started_page')
        elif timer.start_time is None:
            return redirect('paused_page')
        # elif timer.time_left().total_seconds() <= 0:
        #     return redirect('finished_page')
    
    question = get_object_or_404(Question, id=question_id)
    
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        is_correct = user_answer.strip().lower() == question.answer.lower()

        already_correct = Submission.objects.filter(
            user=request.user, question=question, is_correct=True
        ).exists()

        if already_correct:
            messages.info(request, "You have already earned points for this question!")
            broadcast_submission_event(request.user.username, "already")
        else:
            Submission.objects.create(
                user=request.user,
                question=question,
                submitted_answer=user_answer,
                is_correct=is_correct
            )
            if is_correct:
                player_score, created = PlayerScore.objects.get_or_create(user=request.user)
                player_score.score += question.points
                player_score.save()
                messages.success(request, "Correct answer! Well done!")
                broadcast_submission_event(request.user.username, "correct")
            else:
                messages.error(request, "Incorrect answer. Try again!")
                broadcast_submission_event(request.user.username, "incorrect")

    return redirect('questions_in_category', category_name=question.category)

def broadcast_submission_event(username, status):
    """
    Broadcasts a submission event via SSE.
    """
    channel_layer = get_channel_layer()
    message = {
        'username': username,
        'status': status,
    }
    print(f"Broadcasting event: {message}")
    async_to_sync(channel_layer.group_send)(
        "submissions",  # Ensure this matches the group in submission_stream
        {
            "type": "update_scoreboard",  # Event handler name
            "message": message,
        }
    )

@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='login')
def submission_stream(request):
    def event_stream():
        channel_layer = get_channel_layer()

        while True:
            try:
                message = async_to_sync(channel_layer.receive)("submissions")
                if message:
                    print(f"[DEBUG] Sending message to client: {message['message']}")
                    yield f"data: {json.dumps(message['message'])}\n\n"
            except Exception as e:
                print(f"[ERROR] Error in submission_stream: {e}")
            time.sleep(0.1)  # Non-blocking delay

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')




def home_view(request):
    if request.user.is_authenticated:
        return redirect('question_categories')
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been created. You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def question_categories(request):
    timer = ChallengeTimer.objects.first()

    # Redirect non-admin users if timer has not started
    if not request.user.is_staff and not request.user.is_superuser:
        if not timer or timer.start_time is None:  # Timer not started
            return redirect('not_started_page')
        elif not timer.is_active() and timer.start_time is not None:  # Timer paused
            return redirect('paused_page')
        elif timer.is_active() and timer.time_left().total_seconds() <= 0:  # Timer finished
            return redirect('finished_page')

    categories = {
        'HTML': Question.objects.filter(category='HTML'),
        'CSS': Question.objects.filter(category='CSS'),
        'JavaScript': Question.objects.filter(category='JavaScript'),
        'Other': Question.objects.filter(category='Other'),
    }
    return render(request, 'challenges/question_categories.html', {'categories': categories})


@login_required
def questions_in_category(request, category_name):
    timer = ChallengeTimer.objects.first()

    # Redirect non-admin users if timer has not started
    if not request.user.is_staff and not request.user.is_superuser:
        if not timer or timer.start_time is None:  # Timer not started
            return redirect('not_started_page')
        elif not timer.is_active() and timer.start_time is not None:  # Timer paused
            return redirect('paused_page')
        # elif timer.is_active() and timer.time_left().total_seconds() <= 0:  # Timer finished
        #     return redirect('finished_page')

    questions = Question.objects.filter(category=category_name)
    return render(request, 'challenges/questions_in_category.html', {'questions': questions, 'category_name': category_name})


@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='login')
def admin_scoreboard_page(request):
    return render(request, 'challenges/admin_scoreboard.html')


def not_started_page(request):
    timer = ChallengeTimer.objects.first()
    return render(request, 'challenges/not_started.html', {'timer': timer})


@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='login')
def scoreboard_stream(request):
    def event_stream():
        while True:
            scores = PlayerScore.objects.filter(user__is_staff=False, user__is_superuser=False).order_by('-score')
            timer = ChallengeTimer.objects.first()

            if timer and timer.is_active():
                remaining_time = int(timer.time_left().total_seconds())
            else:
                remaining_time = None

            data = {
                'scores': [{'username': s.user.username, 'score': s.score} for s in scores],
                'remaining_time': remaining_time,
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)  # Non-blocking delay

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='login')
def timer_stream(request):
    def event_stream():
        while True:
            timer = ChallengeTimer.objects.first()
            if timer:
                if timer.is_active():
                    remaining_time = int(timer.time_left().total_seconds())
                    if remaining_time <= 0:
                        state = "Finished"
                        remaining_time = 0  # Ensure the timer shows 00:00:00
                    else:
                        state = "Active"
                elif timer.start_time is None and timer.duration:
                    state = "Paused"
                    remaining_time = int(timer.duration.total_seconds())
                else:
                    state = "Finished"
                    remaining_time = 0  # Ensure the timer shows 00:00:00
            else:
                state = "Inactive"
                remaining_time = None

            data = {
                'remaining_time': remaining_time,
                'state': state,
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

@user_passes_test(lambda user: user.is_staff or user.is_superuser)
def timer_manage(request):
    if request.method == "POST":
        data = json.loads(request.body)
        action = data.get("action")

        timer = ChallengeTimer.objects.first()
        if action == "pause" and timer:
            timer.duration = timer.time_left()
            timer.start_time = None
            timer.save()
            return JsonResponse({"status": "success", "message": "Timer paused"})
        elif action == "resume" and timer:
            timer.start_time = now()
            timer.save()
            return JsonResponse({"status": "success", "message": "Timer resumed"})
        elif action == "reset":
            ChallengeTimer.objects.all().delete()
            return JsonResponse({"status": "success", "message": "Timer reset"})

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

@login_required
def view_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    return render(request, 'challenges/questions.html', {'questions': [question]})

def paused_page(request):
    """
    Displayed when the timer is paused.
    """
    return render(request, 'challenges/paused.html')


def finished_page(request):
    """
    Displayed when the timer is finished.
    """
    return render(request, 'challenges/finished.html')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'  # Update this to match your directory structure

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('question_categories')
        return super().get(request, *args, **kwargs)
