from django.urls import path
from challenges import views

urlpatterns = [
    path('', views.question_categories, name='question_categories'),
    path('category/<str:category_name>/', views.questions_in_category, name='questions_in_category'),
    path('submit/<int:question_id>/', views.submit_answer, name='submit_answer'),
    path('scoreboard/', views.admin_scoreboard_page, name='admin_scoreboard'),
    path('admin/set-timer/', views.set_timer, name='set_timer'),
    path('not-started/', views.not_started_page, name='not_started_page'),
    path('scoreboard/stream/', views.scoreboard_stream, name='scoreboard_stream'),
    path('set-timer/', views.set_timer, name='set_timer'),
    path('timer/stream/', views.timer_stream, name='timer_stream'),
    path('timer/manage/', views.timer_manage, name='timer_manage'),
]
