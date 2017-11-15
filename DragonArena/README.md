## Dragon Arena Python basis
Hi everyone, wanted to get a bit up to speed with Python so spent a few hours messing about.

Created a OOP basis for Dragon Arena, didn't have time to finish the drawing implementation due to my promise to Roy ;)

## Version
Make sure you use the latest Python version!
```
$ python -V
Python 3.6.3
```
It could very well be that you have multiple versions, try python3 and python3.6 if you're having problems.

## Pip & Virtual Environments
Python has a sweet package manager, called pip.
Unfortunately, pip can screw up your system when run as root. (internet is full of examples)
So, *DONT RUN PIP AS ROOT*, and run it in a virtual environment :)

A virtual environment (venv) is a folder where a local copy of python, pip, etc and installed pip packages are.
that way, it can't mess with your main system and everything is local.
To create virtual environments in python > 3.3, use:
```
$ python3.6 -m venv [FOLDER_NAME]
```
(I suggest using venv as FOLDER\_NAME name)


To start using your virtualenv, use:
```
$ source [FOLDER_NAME]/bin/activate
(venv) $ 
```
to stop using venv, use:
```
$ deactivate
```

now, when using pip whilst venv is activated, you will install packages in your venv!
My OOP basis uses pygame to draw GUI, but maybe more dependencies will follow.
I've put all dependencies in *requirements.txt* using:
```
(venv) $ pip freeze > requirements.txt
```

To make pip install all requirements, use:
```
(venv) $ pip install -r requirements.txt


## Zakarias Painful lesson
Make sure that when in venv, the python and pip commands work and point to the correct versions.
e.g. you shouldn't need python3 or pip3 in venv.
*MAKE SURE THE PWD DOESN'T CONTAIN SPACES!*
e.g.
```
/home/zak/distributed\ systems/distrbuted-systems-dragon-arena/...
```
WILL NOT WORK because of the space between _distributed and systems_
