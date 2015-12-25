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
settings['sitemap'] = True
settings['sitemap_prettyprint'] = True
settings['rss'] = True
settings['styles'] = []
settings['site_root'] = ''

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
    links = crawl(idir, idir, odir)
    if settings['sitemap']:
        sitemap(odir, links)

# Expect links = {'regular : [], blogs = [{'root' : '', 'links' : []}]}
#        odir should be Path object
def sitemap(odir, links):
    import xml.etree.ElementTree as ET

    urlset = ET.Element('urlset')
    for x in links['regular']:
        path = x
        if settings['site_root']:
            path = settings['site_root'] + path
        url = ET.SubElement(urlset, 'url')
        ET.SubElement(url, 'loc').text = path

    if settings['sitemap_prettyprint']:
        indent(urlset)
    tree = ET.ElementTree(urlset)
    tree.write(str(odir / 'sitemap.xml'), xml_declaration=True)

# Indent XML function for pretty output
def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# Assert idir and odir are directories
def crawl(root, idir, odir):
    links = {'regular' : [], 'blogs' : [] }
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
            new_links = crawl(root, x, y)
            links['regular'] += new_links['regular']
            links['blogs'] += new_links['blogs']
            continue
        #Markdown files
        elif x.suffix == '.md':
            pandoc(root, str(x), str(odir / x.stem) + '.html')
            if settings['duplicate_md']:
                shutil.copy(str(x), str(odir))
                links['regular'] += [str(x)]
        #HTML files
        elif x.suffix == '.html':
            if settings['duplicate_html']:
                shutil.copy(str(x), str(odir))
                links['regular'] += [str(x)]
    return links


if __name__ == "__main__":
   main(sys.argv[1:])
