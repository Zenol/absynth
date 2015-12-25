#!/usr/bin/python3

# This script generate a static website from a tree containing markdown files

import sys, getopt, shutil, subprocess
from pathlib import Path


# Config (TODO : move in config file)
settings = {}
settings['duplicate_md'] = True
settings['duplicate_files'] = True
settings['duplicate_html'] = True
settings['output_extension'] = '.html'
settings['verbose'] = True
settings['pandoc_opts'] = ['--mathjax']
settings['styles'] = []

# Error constants
WRONG_ARG  = 2
WRONG_IDIR = 3
WRONG_ODIR = 4

def verbose(*objs):
    if settings['verbose']:
        print("INFO:", *objs)

def warning(*objs):
    print("WARNING:", *objs, file=sys.stderr)

def help():
    print("usage : extract -i input_directory -o output_directory")


def main(argv):
    input_directory = ''
    output_directory = ''
    try:
        opts, args = getopt.getopt(argv, "hi:o:", [])
    except getopt.GetoptError:
        help()
        sys.exit(WRONG_ARG)
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit()
        elif opt == "-i":
            input_directory = Path(arg)
        elif opt == "-o":
            output_directory = Path(arg)

    if (input_directory == '' or output_directory == ''):
        help()
        sys.exit(WRONG_ARG)

    generate(input_directory, output_directory)

def pandoc(root, ifile, ofile):
    #TODO : Add finer control
    #        '-c', '$SITE/style.css',
    #        '-A', '$SITE/footer.html',
    #        '-B', '$SITE/header.html',

    #Basic command
    pan_cmd = [
        'pandoc',
        '-s',
        '-t', 'html5'
    ] + settings['pandoc_opts']
    #Add styles
    for style in settings['styles']:
        pan_cmd += ['-c', str(Path(root) / style)]

    subprocess.call(pan_cmd + ['-o', ofile] + [ifile])

def generate(idir, odir):
    if (not idir.is_dir()):
        print("Input directory isn't a directory...");
        exit(WRONG_IDIR)
    if (not odir.is_dir()):
        print("Output directory isn't a directory...");
        exit(WRONG_ODIR)
    crawl(idir, idir, odir)

# Assert idir and odir are directories
def crawl(root, idir, odir):
    verbose("Browsing", idir, odir)
    for x in idir.glob('*'):
        if x.is_dir():
            y = odir / x.name
            if (y.is_file()):
                warning("Can't create {0} directory : {0} ignored.".format(str(y)))
            if (not y.exists()):
                try:
                    y.mkdir()
                except:
                    warning("Can't create {0} directory : {0} ignored.".format(str(y)))
            crawl(root, x, y)
            continue
        #Markdown files
        elif x.suffix == '.md':
            pandoc(root, str(x), str(odir / x.stem) + '.html')
            if settings['duplicate_md']:
                shutil.copy(str(x), str(odir))
        #HTML files
        elif x.suffix == '.html':
            if settings['duplicate_html']:
                shutil.copy(str(x), str(odir))


if __name__ == "__main__":
   main(sys.argv[1:])
