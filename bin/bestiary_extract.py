#!/usr/bin/env python
import sys
import os
import os.path
import sh
from pprint import pprint
from optparse import OptionParser

def get_page_heirarchy(filename):
	pdf_data = sh.pdftk(filename, "dump_data")
	rows = []
	record = {}
	for row in pdf_data.split('\n'):
		if row.startswith('BookmarkTitle'):
			title = row.split(": ")[1]
			record['title'] = title.strip()
		if row.startswith('BookmarkLevel'):
			level = int(row.split(": ")[1])
			record['level'] = level
		if row.startswith('BookmarkPageNumber'):
			pn = int(row.split(": ")[1])
			record['page'] = pn
			record['children'] = []
			rows.append(record)
			record = {}
	heir = {'title': "Root", "level": 0, 'pn': 0, "children": []}
	build_heirarchy(heir, rows)
	monsters = None
	after = None
	for rec in heir['children']:
		if monsters != None:
			after = rec
			break
		if rec['title'].startswith('Monsters'):
			monsters = rec
	fix_letters(monsters)
	fix_introduction(monsters)
	fix_duplicate_names(monsters)
	fix_apostrophe(monsters)
	fix_leaf_ray(monsters)
	fix_submonsters(monsters)
	fix_dragons(monsters)
	fix_assassin_vine(monsters)
	return monsters, after['page']

def fix_letters(heir):
	# Bestiary 2, 3 & 4 break bookmarks up into A-Z as letters.
	if len(heir['children'][0]['title']) == 1:
		newchildren = []
		for row in heir['children']:
			newchildren.extend(row['children'])
		heir['children'] = newchildren
	return heir

def fix_introduction(heir):
	for row in heir['children']:
		if row['title'].endswith(' Introduction'):
			title = row['title'].replace(' Introduction', '')
			row['title'] = title

def fix_leaf_ray(heir):
	# There's a defect in the index that includes Variant Leaf Rays as
	# a top level monster.
	for row in heir['children']:
		if row['title'] == 'Variant Leaf Rays':
			heir['children'].remove(row)
			return

def fix_assassin_vine(heir):
	# For some odd reason, Assassin Vine is in the Bestiary twice.  The first
	# one causes a broken dump.
	count = 0
	for row in heir['children']:
		if row['title'] == "Assassin Vine":
			count += 1
	if count > 1:
		for row in heir['children']:
			if row['title'] == "Assassin Vine":
				heir['children'].remove(row)
				return

def fix_duplicate_names(heir):
	# A variety of monsters got expanded in later Bestiaries.  These move them
	# Out of the way
	for row in heir['children']:
		if row['title'] == 'Kyton' and len(row['children']) == 0:
			row['title'] = 'Kyton, Chain Devil'
		if row['title'] == 'Sphinx' and len(row['children']) == 0:
			row['title'] = 'Sphinx, Gynosphinx'
		if row['title'] == 'Rakshasa' and len(row['children']) == 0:
			row['title'] = 'Rakshasa, Standard'
		if row['title'] == 'Familiar' and len(row['children']) == 1:
			row['title'] = 'Familiar, Small'

def fix_apostrophe(heir):
	# Apostrophes in monsters like Will-o'-wisp come out broken
	for row in heir['children']:
		if row['title'].find('&#8217;') > -1:
			row['title'] = row['title'].replace('&#8217;', "'")

def fix_dragons(heir):
	for row in heir['children']:
		if row['title'].find(" Dragon, ") > -1:
			parts = row['title'].split(" Dragon, ")
			row['title'] = "Dragon, %s, %s" %(parts[0], parts[1])
		elif row['title'].startswith("Dragon, "):
			fix_dragons(row)

def fix_submonsters(heir):
	# Later bestiaries each have their own structure rules for monster
	# bookmarks.  This function smooths that out for 1, 2, 3 & 4
	newchildren = []
	filterlist = [
		'Angelic Choirs',
		'Blood Hag Covens',
		'Dragon Age Categories',
		'Dragon Attacks and Speeds',
		'Dragon Ability Scores',
		'Drakainia Spawn',
		'Vampire Spawn',
		'Drow Noble',
		'Graveknight Armor',
		'Shobhad Longrifle',
		'Thriae Merope',
		'Witchfire Covens']
	for row in heir['children']:
		added = []
		if len(row['children']) > 0:
			for child in row['children']:
				if child['title'].startswith("%s" % row['title']) \
						and child['title'].find(' Characters') == -1 \
						and child['title'].find(' Companions') == -1 \
						and child['title'].find(' Traits') == -1 \
						and child['title'].find(' Lords') == -1 \
						and child['title'].find(' Special Abilities') == -1 \
						and child['title'].find('(CR') == -1 \
						and child['title'] not in filterlist:
					added.append(child)
					if child['title'].startswith('Dragon, '):
						for subchild in child['children']:
							if subchild['title'].find(",") > -1:
								added.append(subchild)
				elif child['title'].endswith(", Giant"):
					added.append(child)
				elif row['title'] == "Dragon, Outer" \
						and child['title'].find(" Dragon,") > -1:
					added.append(child)
				# Include Parent:
				#  parent starts on a page before first child exception
				#  Only child same page as parent (Gar, Crawling Hand)
			if len(added) == 0:
				newchildren.append(row)
			else:
				if row['page'] != added[0]['page']:
					newchildren.append(row)
				else:
					if len(added) == 1:
						newchildren.append(row)
				newchildren.extend(added)
		else:
			newchildren.append(row)
	heir['children'] = newchildren

def build_heirarchy(parent, rows):
	parent_level = parent['level']
	while len(rows) > 0:
		rec = rows.pop(0)
		if rec['level'] <= parent_level:
			rows.insert(0, rec)
			return
		elif rec['level'] == parent_level + 1:
			parent['children'].append(rec)
		else:
			rows.insert(0, rec)
			build_heirarchy(parent['children'][-1], rows)

def save_the_beasts(filename, directory, heir, last_page):
	if not os.path.exists(directory):
		os.mkdir(directory)
	for i in range(0, len(heir['children'])):
		row = heir['children'][i]
		next_page = last_page
		if len(heir['children']) > i+1:
			next_page = heir['children'][i+1]['page']
		last_page = next_page - 1
		if last_page < row['page']:
			last_page = row['page']
		title = row['title']
		pagedir = directory
		subdir = title[0]
		pagedir = "%s/%s" % (directory, subdir)
		if not os.path.exists(pagedir):
			os.mkdir(pagedir)
		newfile = "%s/%s.pdf" %(pagedir, row['title'])
		print "%s: %s-%s" %(newfile, row['page'], last_page)
		if os.path.exists(newfile):
			sys.stderr.write("!!!!%s Already Exists\n" % newfile)
		else:
			sh.pdftk(filename, "cat", "%s-%s" %(
				row['page'], last_page), "output", newfile)

def break_out_the_beasts(filename, directory):
	heir, last_page = get_page_heirarchy(filename)
	#pprint(heir)
	save_the_beasts(filename, directory, heir, last_page)

def main():
	usage =  "usage: %prog [options] [pdf filename] [out directory]\n\n"
	usage += "Splits a Paizo Bestiary into 1 file per monster."
	parser = option_parser(usage)
	(options, args) = parser.parse_args()
	if len(args) != 2:
		sys.stderr.write("pdf filename and output directory required.\n")
	break_out_the_beasts(args[0], args[1])

def option_parser(usage):
	parser = OptionParser(usage=usage)
	return parser

if __name__ == "__main__":
	sys.exit(main())

