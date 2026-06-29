# OCR-capture-translate

capture screen and real time translate with OCR

## install the environment

to install the environment, run

```
cd to/your/path/
python -m venv .venv    # use virtual environment if you want
pip install -r req.txt
```

or you can make a virtual environment for this project.

install [MTranServer](https://github.com/xxnuo/MTranServer)
you can install and run it by:

```
npx mtranserver@latest
```
## Run

to run the program

1. run mtranserver
2. run main.py
```
py .\main.py
```

## Remark & ToDo

* [ ]  idk, but hope to increase efficiency
* [ ]  the blackground of the overlay word can be blur to enhance readability
* [X]  the below issue is found that caused by capturing the overlayed result in window, **fixed**

* Overlay being too **messy** and lag & sometime the OCR capture useless info.
* Some info may wrong by OCR or Overlay.
* Some words is too lange, some result is not readable enough
* **Considering to change program lang. or lib.**
