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

        # Get all question IDs and answer IDs
        question_ids = {answer["question_id"] for answer in answers}
        answer_ids = {answer["answer_id"] for answer in answers}

        # Fetch all valid answers in a single query with their questions
        valid_answers = (
            Answer.objects.filter(id__in=answer_ids, question_id__in=question_ids)
            .select_related("question")
            .values_list("id", "question_id")
        )

        # Create a set of valid (question_id, answer_id) pairs
        valid_pairs = {(q_id, a_id) for a_id, q_id in valid_answers}

        # Validate all answers
        for answer in answers:
            if (answer["question_id"], answer["answer_id"]) not in valid_pairs:
                raise serializers.ValidationError(
                    f"Invalid answer selection for question {answer['question_id']}"
                )

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        answers = validated_data.get("answers")

        # Prepare bulk upsert data
        user_answers_to_create = []
        for answer_data in answers:
            user_answers_to_create.append(
                UserAnswer(
                    user=user,
                    question_id=answer_data["question_id"],
                    answer_id=answer_data["answer_id"],
                )
            )

        # Bulk create/update using a single query
        user_answers = UserAnswer.objects.bulk_create(
            user_answers_to_create,
            update_conflicts=True,
            unique_fields=["user", "question"],
            update_fields=["answer"],
        )

        return user_answers


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "order"]
