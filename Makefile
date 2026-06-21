.PHONY: setup data transform quality analysis report all clean
PY=python3
setup:
	$(PY) -m pip install -r requirements.txt
	@echo "R : Rscript analysis/install.R"
data:
	$(PY) -m etl.download
transform: data
	$(PY) -m etl.transform
quality: transform
	$(PY) -m etl.data_quality
analysis: quality
	Rscript analysis/standardisation.R
	Rscript analysis/figures.R
report: analysis
	cd report && pdflatex -interaction=nonstopmode note.tex && pdflatex -interaction=nonstopmode note.tex
all: report
	@echo "Pipeline complet (données réelles CépiDc + INSEE)."
clean:
	rm -rf data/raw/*.json data/raw/*.xls data/processed/*.csv data/processed/*.parquet \
	       data/processed/*.json report/figures/*.png report/*.aux report/*.log \
	       report/*.out report/*.toc __pycache__ etl/__pycache__
