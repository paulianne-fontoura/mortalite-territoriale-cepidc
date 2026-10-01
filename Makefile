.PHONY: setup data transform quality analysis report all clean
PY=python3
# figures en UTF-8 quel que soit le système
export LC_ALL=C.UTF-8
setup:
	$(PY) -m pip install -r requirements.txt
	Rscript analysis/install.R
data:
	$(PY) -m etl.download
transform: data
	$(PY) -m etl.transform
quality: transform
	$(PY) -m etl.data_quality
analysis: quality
	Rscript analysis/standardisation.R
	Rscript analysis/figures.R
	Rscript analysis/chiffres.R
report: analysis
	cd report && pdflatex -interaction=nonstopmode note.tex && pdflatex -interaction=nonstopmode note.tex
all: report
	@echo "Pipeline complet (données réelles CépiDc + INSEE)."
clean:
	rm -rf data/raw/*.json data/raw/*.xls data/processed/*.csv data/processed/*.parquet \
	       data/processed/*.json report/figures/*.png report/*.aux report/*.log \
	       report/*.out report/*.toc __pycache__ etl/__pycache__
