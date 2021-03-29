`Renamer` is tool to rename movies using a clear format.

## Table of content

- [Overview](#Installation)
- [Examples](#Authors)
- [License](#License)

## Overview
It is a tool developed in python 3.
The program loop through a folder containing movies and renames them with the name of the movie and the year.

Its purpose is mainly to remove all the additional information often added in the file name such as the download location, format, available tracks, etc.

The tool uses the IMDB search API to find the movie corresponding to the file. It provides a selection of found movies to the user who can choose to rename the file or not.

In order to keep the original name of the movie, the tool can download a local IMDB database: [title.basics.tsv.gz](https://datasets.imdbws.com/). 

A language recognition algorithm is then used to detect the origin of the film.

## Examples

Simple usage, loop through the directory and search for every filename not respecting the format: ``moviename (year)``:
```
python3 renamer.py -d 'E:\Movies'
```

Check even movies respecting the format:
```
python3 renamer.py -d 'E:\Movies' -a
```
To keep the original language, french in this example, language codes uses ``ISO 639-1``:
```
python3 renamer.py -d 'E:\Movies' -o -l 'fr'
```
Without this option a french movie named as ``Intouchables (2011).mkv`` will be found as ``The Intouchables (2011)``.

The same works for japanese anime where without ``-o -l 'ja'``, movies will be renamed in english.



With this, you can also rename movies with their original names, with:
```
python3 renamer.py -d 'E:\Movies' -o -a -l 'ja'
```
 ``Castle in the Sky (1986).mkv`` is found as ``Tenkû no shiro Rapyuta (1986)``

## Author
* **Théo GOBINET** - [Elec](https://github.com/theogobinet)
## License
Renamer is licensed under the terms of the MIT Licence 
and is available for free - see the [LICENSE.md](LICENSE.md) file for details.