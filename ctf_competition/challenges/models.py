from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now



class ChallengeTimer(models.Model):
    start_time = models.DateTimeField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)  # Duration in HH:MM:SS format

    def is_active(self):
        """Check if the timer is currently active."""
        if not self.start_time or not self.duration:
            return False
        return now() < self.start_time + self.duration

    def time_left(self):
        """Get the remaining time if the timer is active."""
        if not self.is_active():
            return None
        return (self.start_time + self.duration) - now()
    def has_started(self):
        """Check if the timer has started."""
        return self.start_time is not None and now() >= self.start_time

class Question(models.Model):
    CATEGORY_CHOICES = [
        ('HTML', 'HTML'),
        ('CSS', 'CSS'),
        ('JavaScript', 'JavaScript'),
        ('Other', 'Other'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    points = models.IntegerField(default=100)
    answer = models.CharField(max_length=255)  # Correct answer
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    is_multiple_choice = models.BooleanField(default=False)
    option_1 = models.CharField(max_length=255, blank=True, null=True)
    option_2 = models.CharField(max_length=255, blank=True, null=True)
    option_3 = models.CharField(max_length=255, blank=True, null=True)
    option_4 = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title

    def is_valid_option(self, submitted_answer):
        """Check if the submitted answer matches one of the valid options (for MCQs)."""
        options = [self.option_1, self.option_2, self.option_3, self.option_4]
        return submitted_answer.strip() in [opt for opt in options if opt]

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submitted_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.title} - {'Correct' if self.is_correct else 'Wrong'}"

class PlayerScore(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}: {self.score}"
