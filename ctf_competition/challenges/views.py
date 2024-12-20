from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse
from django.utils.timezone import now, timedelta
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Question, Submission, PlayerScore, ChallengeTimer
import json
import time

def set_timer(request):
    if request.method == 'POST':
        try:
            hours = int(request.POST.get('hours', 0) or 0)
            minutes = int(request.POST.get('minutes', 0) or 0)
            seconds = int(request.POST.get('seconds', 0) or 0)
        except ValueError:
            return render(request, 'challenges/set_timer.html', {
                'error': 'Please provide valid numbers for hours, minutes, and seconds.'
            })

        duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        ChallengeTimer.objects.all().delete()
        ChallengeTimer.objects.create(start_time=now(), duration=duration)
        return redirect('admin_scoreboard')

    return render(request, 'challenges/set_timer.html')

def question_list(request):
    questions = Question.objects.all()
    return render(request, 'challenges/questions.html', {'questions': questions})

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

def question_categories(request):
    timer = ChallengeTimer.objects.first()
    categories = {
        'HTML': Question.objects.filter(category='HTML'),
        'CSS': Question.objects.filter(category='CSS'),
        'JavaScript': Question.objects.filter(category='JavaScript'),
        'Other': Question.objects.filter(category='Other'),
    }
    return render(request, 'challenges/question_categories.html', {'categories': categories})

def questions_in_category(request, category_name):
    questions = Question.objects.filter(category=category_name)
    return render(request, 'challenges/questions_in_category.html', {'questions': questions, 'category_name': category_name})

def admin_scoreboard_page(request):
    return render(request, 'challenges/admin_scoreboard.html')

def not_started_page(request):
    timer = ChallengeTimer.objects.first()
    return render(request, 'challenges/not_started.html', {'timer': timer})

def scoreboard_stream(request):
    print("[DEBUG] scoreboard_stream called")
    def event_stream():
        while True:
            print("[DEBUG] Preparing scoreboard data...")
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
            print("[DEBUG] Sending data:", data)  # Add this
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

@user_passes_test(lambda user: user.is_staff or user.is_superuser)
def set_timer(request):
    if request.method == 'POST':
        try:
            hours = int(request.POST.get('hours', 0) or 0)
            minutes = int(request.POST.get('minutes', 0) or 0)
            seconds = int(request.POST.get('seconds', 0) or 0)
        except ValueError:
            return render(request, 'challenges/set_timer.html', {
                'error': 'Please provide valid numbers for hours, minutes, and seconds.'
            })

        duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        ChallengeTimer.objects.all().delete()
        ChallengeTimer.objects.create(start_time=now(), duration=duration)
        return redirect('admin_scoreboard')

    return render(request, 'challenges/set_timer.html')