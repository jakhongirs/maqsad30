from django.core.management.base import BaseCommand

from apps.main.models import Challenge, SuperChallenge
from apps.notification.models import (
    ChallengeNotificationTemplate,
    SuperChallengeNotificationTemplate,
)


class Command(BaseCommand):
    help = (
        "Initialize notification templates for existing challenges and super challenges"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation of templates even if they already exist",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        self.stdout.write(self.style.NOTICE("Initializing notification templates..."))

        # Initialize challenge notification templates
        self._init_challenge_templates(force)

        # Initialize super challenge notification templates
        self._init_super_challenge_templates(force)

        self.stdout.write(
            self.style.SUCCESS("Notification templates initialized successfully!")
        )

    def _init_challenge_templates(self, force):
        """Initialize notification templates for regular challenges."""
        challenges = Challenge.objects.all()
        created_count = 0
        skipped_count = 0

        for challenge in challenges:
            # Check if template already exists
            template_exists = ChallengeNotificationTemplate.objects.filter(
                challenge=challenge
            ).exists()

            if template_exists and not force:
                skipped_count += 1
                continue

            # Default message template
            default_message = (
                f"Bugun {challenge.title} mashqini bajardingizmi? Bajargan boʻlsangiz belgilang.\n\n"
                f"Belgilash muddati: {challenge.start_time.strftime('%H:%M')} dan "
                f"{challenge.end_time.strftime('%H:%M')} gacha"
            )

            # Create or update template
            if template_exists:
                template = ChallengeNotificationTemplate.objects.get(
                    challenge=challenge
                )
                template.message = default_message
                template.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated template for challenge: {challenge.title}"
                    )
                )
            else:
                ChallengeNotificationTemplate.objects.create(
                    challenge=challenge,
                    message=default_message,
                    is_active=True,
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created template for challenge: {challenge.title}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Challenge templates: {created_count} created, {skipped_count} skipped"
            )
        )

    def _init_super_challenge_templates(self, force):
        """Initialize notification templates for super challenges."""
        super_challenges = SuperChallenge.objects.all()
        created_count = 0
        skipped_count = 0

        for super_challenge in super_challenges:
            # Check if template already exists
            template_exists = SuperChallengeNotificationTemplate.objects.filter(
                super_challenge=super_challenge
            ).exists()

            if template_exists and not force:
                skipped_count += 1
                continue

            # Default message templates
            default_general_message = (
                f"{super_challenge.title} — super chellenjning barcha shartlarini yakunladingizmi?\n\n"
                f"Yutugʻingizni belgilab qoʻyishni unutmang.\n\n"
                f"Belgilash muddati: 19:00 dan 23:59 gacha"
            )

            default_warning_message = (
                f'⚠️ Siz bugun "{super_challenge.title}" topshiriqlarini toʻliq bajarmadingiz.\n\n'
                f"Agar yana bir marta o'tkazib yuborsangiz, natijalaringiz 0 ga tushadi. "
                f"Boʻshashmang, harakatni davom ettiring!"
            )

            default_failure_message = (
                f"❌ Natijangiz 0 ga tushdi!\n\n"
                f'Siz 2 marta "{super_challenge.title}" shartlarini toʻliq bajarmadingiz.\n\n'
                f'Demak, "{super_challenge.title}"ni toʻliq oʻtash imkoniyati yoʻqoldi. '
                f"Lekin tajriba orttirildi! Oʻzingiz davom etsangiz boʻladi."
            )

            # Create or update template
            if template_exists:
                template = SuperChallengeNotificationTemplate.objects.get(
                    super_challenge=super_challenge
                )
                template.general_message = default_general_message
                template.progress_warning_message = default_warning_message
                template.failure_message = default_failure_message
                template.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated template for super challenge: {super_challenge.title}"
                    )
                )
            else:
                SuperChallengeNotificationTemplate.objects.create(
                    super_challenge=super_challenge,
                    general_message=default_general_message,
                    progress_warning_message=default_warning_message,
                    failure_message=default_failure_message,
                    is_active=True,
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created template for super challenge: {super_challenge.title}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Super challenge templates: {created_count} created, {skipped_count} skipped"
            )
        )
