from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Question
from .serializers import (
    QuestionSerializer,
    UserAnswerCreateSerializer,
    UserAnswerResponseSerializer,
)


class QuestionListView(generics.ListAPIView):
    """
    API endpoint to list all active onboarding questions with their answers.
    """

    queryset = Question.objects.filter(is_active=True).prefetch_related("answers")
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserAnswersBulkCreateView(generics.CreateAPIView):
    """
    API endpoint to create or update multiple user answers in one request.
    """

    serializer_class = UserAnswerCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_answers = serializer.save()

        # Use response serializer for the created instances
        response_serializer = UserAnswerResponseSerializer(user_answers, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
