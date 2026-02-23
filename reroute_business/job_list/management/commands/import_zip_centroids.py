import csv

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from reroute_business.job_list.models import ZipCentroid


class Command(BaseCommand):
    help = "Import ZIP centroid CSV data into ZipCentroid. Expected columns: zip_code, latitude, longitude"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--batch-size", type=int, default=2000)

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        batch_size = options["batch_size"]

        if batch_size <= 0:
            raise CommandError("--batch-size must be greater than 0")

        rows = []
        inserted_total = 0
        updated_total = 0
        skipped_total = 0

        try:
            with open(csv_path, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                required = {"zip_code", "latitude", "longitude"}
                if not required.issubset(set(reader.fieldnames or [])):
                    raise CommandError("CSV must include headers: zip_code, latitude, longitude")

                for idx, row in enumerate(reader, start=2):
                    zip_code = (row.get("zip_code") or "").strip()
                    lat_raw = (row.get("latitude") or "").strip()
                    lon_raw = (row.get("longitude") or "").strip()

                    if not zip_code:
                        skipped_total += 1
                        continue

                    try:
                        latitude = float(lat_raw)
                        longitude = float(lon_raw)
                    except (TypeError, ValueError):
                        self.stderr.write(f"Skipping row {idx}: invalid latitude/longitude")
                        skipped_total += 1
                        continue

                    rows.append(
                        ZipCentroid(
                            zip_code=zip_code,
                            geo_point=Point(longitude, latitude, srid=4326),
                        )
                    )

                    if len(rows) >= batch_size:
                        inserted, updated = self._flush(rows, batch_size)
                        inserted_total += inserted
                        updated_total += updated
                        rows.clear()

                if rows:
                    inserted, updated = self._flush(rows, batch_size)
                    inserted_total += inserted
                    updated_total += updated

        except FileNotFoundError as exc:
            raise CommandError(f"CSV file not found: {csv_path}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"ZIP centroid import complete. Inserted: {inserted_total}, "
                f"Updated: {updated_total}, Skipped: {skipped_total}."
            )
        )

    @staticmethod
    @transaction.atomic
    def _flush(rows, batch_size):
        deduped_by_zip = {}
        for row in rows:
            deduped_by_zip[row.zip_code] = row
        unique_rows = list(deduped_by_zip.values())
        zip_codes = [row.zip_code for row in unique_rows]
        existing_count = ZipCentroid.objects.filter(zip_code__in=zip_codes).count()

        ZipCentroid.objects.bulk_create(
            unique_rows,
            batch_size=batch_size,
            update_conflicts=True,
            update_fields=["geo_point"],
            unique_fields=["zip_code"],
        )
        inserted = len(unique_rows) - existing_count
        updated = existing_count
        return inserted, updated
