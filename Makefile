install: requirements.txt
	pip3 install -r requirements.txt

run: main.py
	python3 -m streamlit run main.py