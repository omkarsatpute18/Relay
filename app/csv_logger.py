
import csv
import os
import uuid
from pathlib import Path


class CSVLogger:

    COLUMNS = [
        "request_id",
        "scenario",
        "source",
        "start_time",
        "first_token_ms",
        "total_ms",
        "status",
        "retries",
        "tokens_in",
        "tokens_out",
        "retrieval_setting",
        "answer_grade"
    ]

    VALID_STATUSES = {
        "ok",
        "rate_limited",
        "timeout",
        "error"
    }

    def __init__(self, filepath="results/results.csv"):

        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.filepath.exists():
            with open(
                self.filepath,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=self.COLUMNS
                )
                writer.writeheader()

    def log_request(
        self,
        scenario,
        source,
        start_time,
        first_token_ms,
        total_ms,
        status,
        retries,
        tokens_in,
        tokens_out,
        retrieval_setting,
        answer_grade=""
    ):

        if status not in self.VALID_STATUSES:
            status = "error"

        if answer_grade not in {
            "",
            "correct",
            "wrong",
            "refused_correctly",
            "refused_wrongly"
        }:
            answer_grade = ""

        row = {
            "request_id": str(uuid.uuid4()),
            "scenario": scenario,
            "source": source,
            "start_time": start_time,
            "first_token_ms": first_token_ms,
            "total_ms": total_ms,
            "status": status,
            "retries": retries,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "retrieval_setting": retrieval_setting,
            "answer_grade": answer_grade
        }

        with open(
            self.filepath,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=self.COLUMNS
            )
            writer.writerow(row)

        return row["request_id"]
