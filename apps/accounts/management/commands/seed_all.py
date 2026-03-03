from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run all seed commands in sequence for full pagination-ready test data."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=str, default="2025-2026")
        parser.add_argument("--prefix", type=str, default="seed")
        parser.add_argument("--password", type=str, default="Pass1234!")
        parser.add_argument("--terms", type=str, default="first,second,third")

        parser.add_argument("--accounts-teachers", type=int, default=120)
        parser.add_argument("--accounts-parents", type=int, default=200)
        parser.add_argument("--teachers", type=int, default=120)
        parser.add_argument("--staff", type=int, default=100)
        parser.add_argument("--students", type=int, default=300)
        parser.add_argument("--students-per-section", type=int, default=40)
        parser.add_argument("--grades", type=str, default="1,2,3,4,5")
        parser.add_argument("--sections", type=str, default="A,B")
        parser.add_argument("--invoices", type=int, default=300)
        parser.add_argument("--expenditures", type=int, default=150)
        parser.add_argument("--attendance-days", type=int, default=90)

        parser.add_argument(
            "--reset-enrollments",
            action="store_true",
            help="Reset enrollments while seeding academics.",
        )
        parser.add_argument(
            "--reset-grades",
            action="store_true",
            help="Reset grades for selected year/terms before seeding.",
        )
        parser.add_argument(
            "--skip-weekends",
            action="store_true",
            help="Skip weekend attendance records.",
        )

    def handle(self, *args, **options):
        year = options["year"]
        prefix = options["prefix"]
        password = options["password"]
        terms = options["terms"]

        try:
            self.stdout.write(self.style.NOTICE("1/8 Seeding accounts..."))
            call_command(
                "seed_account",
                teachers=options["accounts_teachers"],
                parents=options["accounts_parents"],
                password=password,
                prefix=prefix,
            )

            self.stdout.write(self.style.NOTICE("2/8 Seeding teachers..."))
            call_command(
                "seed_teachers",
                count=options["teachers"],
                password=password,
                prefix=prefix,
            )

            self.stdout.write(self.style.NOTICE("3/8 Seeding staff..."))
            call_command(
                "seed_staff",
                count=options["staff"],
                password=password,
                prefix=prefix,
            )

            self.stdout.write(self.style.NOTICE("4/8 Seeding students..."))
            call_command(
                "seed_students",
                count=options["students"],
                prefix=prefix,
            )

            self.stdout.write(self.style.NOTICE("5/8 Seeding academics..."))
            call_command(
                "seed_academics",
                year=year,
                grades=options["grades"],
                sections=options["sections"],
                students_per_section=options["students_per_section"],
                reset_enrollments=options["reset_enrollments"],
            )

            self.stdout.write(self.style.NOTICE("6/8 Seeding grades..."))
            call_command(
                "seed_grades",
                year=year,
                terms=terms,
                reset=options["reset_grades"],
            )

            self.stdout.write(self.style.NOTICE("7/8 Seeding finance..."))
            call_command(
                "seed_finance",
                invoices=options["invoices"],
                expenditures=options["expenditures"],
                year=year,
                prefix=prefix.upper(),
            )

            self.stdout.write(self.style.NOTICE("8/8 Seeding attendance..."))
            call_command(
                "seed_attendance",
                days=options["attendance_days"],
                skip_weekends=options["skip_weekends"],
            )

        except Exception as exc:
            raise CommandError(f"seed_all failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("seed_all complete."))
