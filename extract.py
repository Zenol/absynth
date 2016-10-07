#!/usr/bin/python3

# This script generate a static website from a tree containing markdown files

import sys, getopt, shutil, subprocess
import yaml
from pathlib import Path
import dateutil.parser
import datetime

# Config
settings = {}

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
    global settings
    with open('settings.yaml', 'r') as stream:
        settings = yaml.load(stream)
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

def pandoc(root, ifile, ofile, level = 0):
    # Look for header or footer
    hf = []
    if settings['auto_header']:
        file = root / settings['auto_header']
        if file.exists():
            hf += ['-B', str(file)]
    if settings['auto_footer']:
        file = root / settings['auto_footer']
        if file.exists():
            hf += ['-A', str(file)]
    if settings['auto_style']:
        file = root / settings['auto_style']
        if file.exists():
            hf += ['-c', '../' * level + settings['auto_style']]
    #Basic command
    pan_cmd = [
        'pandoc',
        '-s',
        '-t', 'html5'
    ] + hf + settings['pandoc_opts']
    # Add styles
    for style in settings['styles']:
        pan_cmd += ['-c',  '../' * level + style]
    subprocess.call(pan_cmd + ['-o', ofile] + [ifile])

def generate(idir, odir):
    global settings
    if (not idir.is_dir()):
        print("Input directory isn't a directory...");
        exit(WRONG_IDIR)
    if (not odir.is_dir()):
        print("Output directory isn't a directory...");
        exit(WRONG_ODIR)

    # Load settings located in input directory
    settings_file = idir / settings['auto_settings']
    if settings['auto_settings'] and settings_file.exists():
        with open(str(settings_file), 'r') as stream:
            new_settings = yaml.load(stream)
            if new_settings:
                settings.update(new_settings)

    settings.update()
    links = crawl(idir, idir, odir)
    if settings['sitemap']:
        sitemap(odir, links)

# Utilitary function for sitemap and rss. Build the absolute path (if possible)
# to the resource.
def build_path_string(path):
    if settings['site_root']:
        path = str(Path(settings['site_root']) / path)
    return str(path)

# Build the rss feed of a blog
def rss(odir, links):
    import xml.etree.ElementTree as ET
    import hashlib

    # Root
    rss = ET.Element('rss')
    ET.SubElement(rss, 'generator').text = 'Absynth'
    ET.SubElement(rss, 'docs').text = 'http://backend.userland.com/rss'
    channel = ET.SubElement(rss, 'channel')

    # If some values are missing, set them to empty
    ET.SubElement(channel, 'title').text = settings['blog_title']
    ET.SubElement(channel, 'link').text = str(Path(settings['site_root']) / links['root'])
    ET.SubElement(channel, 'description').text = settings['blog_description']
    if settings['rss_category']:
        ET.SubElement(channel, 'category').text = settings['rss_category']
    if settings['rss_language']:
        ET.SubElement(channel, 'language').text = settings['rss_language']

    # Add links to articles
    for article in links['articles'][:settings['rss_limit']]:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = article['title']
        ET.SubElement(item, 'link').text = build_path_string(article['file'])
        ET.SubElement(item, 'description').text = article['abstract']
        if article['date']:
            ET.SubElement(item, 'pubDate').text = article['date']
        if settings['rss_guid_hash']:
            hash_fct = hashlib.sha256()
            with open(str(article['ifile']), mode='rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_fct.update(chunk)
            guid = ET.SubElement(item, 'guid')
            guid.text = hash_fct.hexdigest()
            guid.set('isPermaLink', 'false')

    tree = ET.ElementTree(rss)
    tree.write(str(odir / 'rss.xml'), xml_declaration = True)

# Expect links = {'regular : [], blogs = [{'root' : '', 'articles' : []}]}
#        odir should be Path object
def sitemap(odir, links):
    import xml.etree.ElementTree as ET

    urlset = ET.Element('urlset')

    # Regular link
    for x in links['regular']:
        url = ET.SubElement(urlset, 'url')
        ET.SubElement(url, 'loc').text = build_path_string(x)

    # Blogs
    for blog in links['blogs']:
        for article in blog['articles']:
            url = ET.SubElement(urlset, 'url')
            path = Path(blog['root']) / article['file']
            ET.SubElement(url, 'loc').text = build_path_string(path)

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

def compute_link(root, ifile, ext):
    ifile = ifile.relative_to(root)
    if ext:
        ifile = ifile.with_suffix(ext)
    return str(ifile)

# Assert idir and odir are directories
def crawl(root, idir, odir, level = 0):
    links = {'regular' : [], 'blogs' : [] }

    # Display a message in verbose mode
    verbose("Browsing", idir, odir)

    # Look at all the files in the directory
    for x in idir.glob('*'):
        # GIT
        if x.name == '.git':
            continue
        # Sub directory
        if x.is_dir():
            y = odir / x.name
            if (y.is_file()):
                warning("Can't create {0} directory : {0} ignored.".format(str(y)))
            if (not y.exists()):
                try:
                    y.mkdir()
                except:
                    warning("Can't create {0} directory : {0} ignored.".format(str(y)))
            # Blog mode :
            if x.name == 'blog':
                new_links = blog(root, x, y, level + 1)
            else:
                new_links = crawl(root, x, y, level + 1)
            links['regular'] += new_links['regular']
            links['blogs'] += new_links['blogs']
            continue
        # A file used by the script
        if root == idir:
            if str(x.name) in settings['exclude_files']:
                continue
            if settings['auto_header'] and settings['auto_header'] == str(x.name):
                continue
            if settings['auto_footer'] and settings['auto_footer'] == str(x.name):
                continue
            if settings['auto_style'] and settings['auto_style'] == str(x.name):
                shutil.copy(str(x), str(odir))
        # Skip files from exclude_files
        if compute_link(root, x, "") in settings['exclude_files']:
            continue
        # Markdown files
        if x.suffix == '.md':
            pandoc(root, str(x),
                   str(odir / x.stem) + settings['output_extension'], level)
            if settings['duplicate_md']:
                shutil.copy(str(x), str(odir))
            links['regular'] += [compute_link(root, x, settings['output_extension'])]
        # HTML files
        elif x.suffix == '.html' or x.suffix == 'htm':
            if settings['duplicate_html']:
                shutil.copy(str(x), str(odir))
                links['regular'] += [compute_link(root, x, None)]
        elif x.suffix == '.css' and x.name in settings['styles']:
            shutil.copy(str(x), str(odir))
        elif settings['duplicate_files']:
            shutil.copy(str(x), str(odir))
    return links

# Assert idir and odir are directories
def blog(root, idir, odir, level = 0):
    import tempfile

    root_name = str(idir.relative_to(root))
    links = {'articles': [], 'root' : root_name}

    # Generate articles
    for articlef in idir.glob('*'):
        # GIT
        if articlef.name == '.git':
            continue
        if not articlef.is_dir():
            continue
        # Create article folder
        article = articlef.name
        if not (odir / article).exists():
            (odir / article).mkdir()
        for file in articlef.glob('*'):
            # GIT
            if file.name == '.git':
                continue
            # Data folder
            if file.is_dir() and file.name == 'data':
                new_data_dir = odir / article / file.name
                if new_data_dir.exists():
                    shutil.rmtree(str(new_data_dir))
                shutil.copytree(str(file), str(new_data_dir))
            if file.is_file() and file.suffix == '.md':
                lang = file.stem
                ifile = file
                ofile = odir / article / (lang  + '.html')
                pandoc(root,
                       str(ifile),
                       str(ofile),
                       level)
                if settings['duplicate_md']:
                    shutil.copy(str(file), str(odir / article))
                # Article's description
                article_desc = {'folder' : article,
                                'lang'   : lang,
                                'title'  : article,
                                'abstract'    : '',
                                'date'   : '',
                                'date_object' : None,
                                'file'   : compute_link(idir, ifile, settings['output_extension']),
                                'ifile'  : ifile}
                # Parse article's yaml
                info = {}
                with open(str(ifile), 'r') as stream:
                    yaml_input = ''
                    if stream.readline()[:3] == '---':
                        while True:
                            line = stream.readline()
                            if line[:3] == '...' or line[:3] == '---':
                                break
                            yaml_input += line
                    info = yaml.load(yaml_input)
                # Fusione les informations
                if info:
                    article_desc.update(info)
                try:
                    article_desc.update(
                        {'date_object' : dateutil.parser.parse(article_desc['date']).date()})
                except:
                    warning('Invalide date format for ' + article_desc['folder'])
                links['articles'] += [article_desc]
    # Generate index page
    tmp_file = tempfile.NamedTemporaryFile(prefix='absynth_', delete = False, mode='w+')
    tmp_file.write('---\n'
                   'title: ' + settings['blog_title'] + '\n'
                   '...\n'
                   '# ' + settings['blog_h1'] + '\n')
    links['articles'].sort(key = lambda article_desc:
                           article_desc['date_object'] if article_desc['date_object']
                           else datetime.date(datetime.MINYEAR, 1, 1),
                           reverse = settings['reverse_order'])
    for article in links['articles']:
        date = ''
        if article['date']:
            date = article['date'] + ' - '
        tmp_file.write('*  '
                       + date
                       + '[' + article['lang'].upper()
                       + ' - '  + article['title'] + ']('
                       + article['file']
                       + ')\n')
    tmp_file.close()
    pandoc(root, tmp_file.name, str(odir / ('index' + settings['output_extension'])), level)
    Path(tmp_file.name).unlink()

    #Generate RSS feed
    rss(odir, links)

    return {'regular' : [], 'blogs' : [links] }

if __name__ == "__main__":
   main(sys.argv[1:])
