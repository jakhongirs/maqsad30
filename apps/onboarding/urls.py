from django.urls import path

from .views import FAQListView, QuestionListView, UserAnswersBulkCreateView

app_name = "onboarding"

urlpatterns = [
    path("questions/", QuestionListView.as_view(), name="question-list"),
    path(
        "user-answers/create/",
        UserAnswersBulkCreateView.as_view(),
        name="user-answer-create",
    ),
    path("faqs/", FAQListView.as_view(), name="faq-list"),
]
