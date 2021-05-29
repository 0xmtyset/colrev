.PHONY : status search backward_search cleanse_records screen data

help :
	@echo "Usage: make [command]"
	@echo "    help"
	@echo "        Show this help description"

cli :
	docker-compose up & gnome-terminal -e "bash -c \"docker-compose run --rm review_template_python3 /bin/bash\""

initialize :
	python3 analysis/initialize.py

validate :
	cd data && pre-commit run -a

status :
	python3 analysis/status.py

reformat_bibliography :
	python3 analysis/reformat_bibliography.py

trace_hash_id :
	python3 analysis/trace_hash_id.py

# to test:

trace_entry :
	python3 analysis/trace_entry.py

combine_individual_search_results :
	python3 analysis/combine_individual_search_results.py

cleanse_records :
	python3 analysis/cleanse_records.py

screen_sheet :
	python3 analysis/screen_sheet.py

screen_1 :
	python3 analysis/screen_1.py

screen_2 :
	python3 analysis/screen_2.py

data_sheet :
	python3 analysis/data_sheet.py

data_pages :
	python3 analysis/data_pages.py

backward_search :
	python3 analysis/backward_search.py

merge_duplicates :
	python3 analysis/merge_duplicates.py

acquire_pdfs :
	python3 analysis/acquire_pdfs.py

# development:

validate_pdfs :
	python3 analysis/validate_pdfs.py

sample_profile :
	python3 analysis/sample_profile.py
