from rest_framework import serializers

from .models import FAQ, Answer, Question, UserAnswer


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "text", "order"]


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "title", "order", "answers"]


class UserAnswerResponseSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(source="question.id")
    answer_id = serializers.IntegerField(source="answer.id")

    class Meta:
        model = UserAnswer
        fields = ["question_id", "answer_id"]


class AnswerDataSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_id = serializers.IntegerField()


class UserAnswerCreateSerializer(serializers.Serializer):
    answers = AnswerDataSerializer(many=True, write_only=True)

    def validate(self, data):
        answers = data.get("answers", [])

        for answer in answers:
            question_id = answer["question_id"]
            answer_id = answer["answer_id"]

            # Validate that answer belongs to the question
            if not Answer.objects.filter(
                question_id=question_id, id=answer_id
            ).exists():
                raise serializers.ValidationError(
                    f"Invalid answer selection for question {question_id}"
                )

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        answers = validated_data.get("answers")
        user_answers = []

        for answer_data in answers:
            question_id = answer_data["question_id"]
            answer_id = answer_data["answer_id"]

            user_answer, _ = UserAnswer.objects.update_or_create(
                user=user, question_id=question_id, defaults={"answer_id": answer_id}
            )
            user_answers.append(user_answer)

        return user_answers


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "order"]
