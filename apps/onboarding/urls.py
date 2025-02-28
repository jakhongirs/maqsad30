from django.urls import path

from .views import QuestionListView, UserAnswersBulkCreateView

app_name = "onboarding"

urlpatterns = [
    path("questions/", QuestionListView.as_view(), name="question-list"),
    path(
        "user-answers/create/",
        UserAnswersBulkCreateView.as_view(),
        name="user-answer-create",
    ),
]
