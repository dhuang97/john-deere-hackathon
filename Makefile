ifeq ($(OS),Windows_NT)
	PYTHONTYPE := python
	PIPTYPE := pip
else
	PYTHONTYPE := python3
	PIPTYPE := pip3
endif

install: requirements.txt
	$(PIPTYPE) install -r requirements.txt

run: main.py
	$(PYTHONTYPE) -m streamlit run main.py