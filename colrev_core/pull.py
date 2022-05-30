#! /usr/bin/env python
from colrev_core.process import Process
from colrev_core.process import ProcessType


class Pull(Process):
    def __init__(self, *, REVIEW_MANAGER):
        super().__init__(REVIEW_MANAGER=REVIEW_MANAGER, type=ProcessType.explore)

    def main(self, *, records_only: bool = False, project_only: bool = False) -> None:

        if project_only:
            self.pull_project()
        elif records_only:
            self.pull_records_from_index()
        else:
            self.pull_project()
            self.pull_records_from_index()

        return

    def pull_project(self) -> None:
        try:
            git_repo = self.REVIEW_MANAGER.REVIEW_DATASET.get_repo()
            origin = git_repo.remotes.origin
            self.REVIEW_MANAGER.logger.info(
                f"Pull changes from {git_repo.remotes.origin}"
            )
            res = origin.pull()
        except AttributeError:
            self.REVIEW_MANAGER.logger.info("No remote detected for pull")
            pass
            return

        if 4 == res[0].flags:
            self.REVIEW_MANAGER.logger.info("No updates")
        elif 64 == res[0].flags:
            self.REVIEW_MANAGER.logger.info("Updated CoLRev repository")
        else:
            self.REVIEW_MANAGER.logger.info(f"Returned flag {res[0].flags}")

    def pull_records_from_index(self) -> None:
        from colrev_core.prep import Preparation, PrepRecord
        from pathos.multiprocessing import ProcessPool
        import multiprocessing as mp

        self.REVIEW_MANAGER.logger.info("Pull records from index")

        # Note : do not use named argument (used in multiprocessing)
        def pull_record(record):
            previous_status = record["colrev_status"]
            # TODO : remove the following
            previous_source_url = record.get("source_url", "")
            previouscolrev_pdf_id = record.get("colrev_pdf_id", "")
            prev_dblp_key = record.get("dblp_key", "")

            RECORD = PrepRecord(record)
            RETRIEVED_RECORD = PREPARATION.get_record_from_local_index(RECORD)
            source_info = "LOCAL_INDEX"
            if "CURATED:" in RETRIEVED_RECORD.data["colrev_masterdata_provenance"]:
                source_info = RETRIEVED_RECORD.data[
                    "colrev_masterdata_provenance"
                ].replace("CURATED:", "")
            RECORD.merge(RETRIEVED_RECORD, source_info)

            record = RECORD.get_data()
            record["colrev_status"] = previous_status

            if "" != previous_source_url:
                record["source_url"] = previous_source_url
            if "" != previouscolrev_pdf_id:
                record["colrev_pdf_id"] = previouscolrev_pdf_id
            if "" != prev_dblp_key:
                record["dblp_key"] = prev_dblp_key
            return record

        self.REVIEW_MANAGER.logger.info("Load records")

        PREPARATION = Preparation(
            REVIEW_MANAGER=self.REVIEW_MANAGER, notify_state_transition_process=False
        )
        records = self.REVIEW_MANAGER.REVIEW_DATASET.load_records_dict()

        self.REVIEW_MANAGER.logger.info("Update records based on LocalIndex")

        pool = ProcessPool(nodes=mp.cpu_count() - 1)
        records_list = pool.map(pull_record, records.values())
        pool.close()
        pool.join()
        pool.clear()

        # TODO : test the following line
        records = {r["ID"]: r for r in records_list}
        self.REVIEW_MANAGER.REVIEW_DATASET.save_records_dict(records=records)
        self.REVIEW_MANAGER.REVIEW_DATASET.add_record_changes()
        self.REVIEW_MANAGER.create_commit(msg="Update records")

        return


if __name__ == "__main__":
    pass