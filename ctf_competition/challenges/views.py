from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse
from django.utils.timezone import now, timedelta
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Question, Submission, PlayerScore, ChallengeTimer
import json
import time


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
        if not timer or not timer.has_started():
            return redirect('not_started_page')

    questions = Question.objects.all()
    return render(request, 'challenges/questions.html', {'questions': questions})


@login_required
def submit_answer(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        is_correct = user_answer.strip().lower() == question.answer.lower()

        already_correct = Submission.objects.filter(
            user=request.user, question=question, is_correct=True
        ).exists()

        if not already_correct:
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

    return redirect('questions_in_category', category_name=question.category)


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
        if not timer or not timer.has_started():
            return redirect('not_started_page')

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
        if not timer or not timer.has_started():
            return redirect('not_started_page')

    questions = Question.objects.filter(category=category_name)
    return render(request, 'challenges/questions_in_category.html', {'questions': questions, 'category_name': category_name})


@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='login')
def admin_scoreboard_page(request):
    return render(request, 'challenges/admin_scoreboard.html')


def not_started_page(request):
    timer = ChallengeTimer.objects.first()
    return render(request, 'challenges/not_started.html', {'timer': timer})


@user_passes_test(lambda user: user.is_staff or user.is_superuser, login_url='login')
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
                    state = "Active"
                    remaining_time = int(timer.time_left().total_seconds())
                elif timer.start_time is None and timer.duration:
                    state = "Paused"
                    remaining_time = int(timer.duration.total_seconds())
                else:
                    state = "Finished"
                    remaining_time = None
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