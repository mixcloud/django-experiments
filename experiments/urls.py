from django.urls import path
from experiments import views

urlpatterns = [
    path('goal/<str:goal_name>/<str:cache_buster>/', views.record_experiment_goal, name="experiment_goal"),
    path('confirm_human/', views.confirm_human, name="experiment_confirm_human"),
    path('change_alternative/<str:experiment_name>/<str:alternative_name>/', views.change_alternative, name="experiment_change_alternative"),
]
