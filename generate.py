#!/usr/bin/env python3

import datetime
import git
import glob
import io
import json
import os
from PIL import Image
import sys
import urllib.parse
import yaml

# No py 2
if(sys.version_info.major != 3):
	print("This is Python %d!\nPlease use Python 3!" % sys.version_info.major)
	exit()

# Add new games and such here
sections = {
	"3deins": {
		"name": "3DEins",
		"icon": 0
	},
	"3dvier": {
		"name": "3DVier",
		"icon": 1
	},
	"3dzwei": {
		"name": "3DZwei",
		"icon": 2
	},
	"characters": {
		"name": "Characters",
		"icon": 3
	}
}

# Convert names to lowercase alphanumeric + underscore and hyphen
def webName(name):
	name = name.lower()
	out = ""
	for letter in name:
		if letter in "abcdefghijklmnopqrstuvwxyz0123456789-_.":
			out += letter
		elif letter == " ":
			out += "-"
	return out

def getSection(path):
	for section in sections:
		if section + os.path.sep in path:
			return section
	return ""

def getName(path):
	for section in sections:
		if section + os.path.sep in path:
			return sections[section]["name"]
	return ""

def getDefaultIcon(path):
	for section in sections:
		if section + os.path.sep in path:
			return sections[section]["icon"]
	return -1

# Read version from old unistore
unistoreOld = {}
if os.path.exists(os.path.join("docs", "unistore", "ut-game-sets.unistore")):
	with open(os.path.join("docs", "unistore", "ut-game-sets.unistore"), "r", encoding="utf8") as file:
		unistoreOld = json.load(file)

# Create UniStore base
unistore = {
	"storeInfo": {
		"title": "Universal-Team Game Sets",
		"author": "Universal-Team",
		"url": "https://game-sets.universal-team.net/unistore/ut-game-sets.unistore",
		"file": "ut-game-sets.unistore",
		"sheetURL": "https://game-sets.universal-team.net/unistore/ut-game-sets.t3x",
		"sheet": "ut-game-sets.t3x",
		"description": "Additional card sets for Universal-Team games\n\n(The 'Console' is the game)",
		"version": 3,
		"revision": 0 if ("storeInfo" not in unistoreOld or "revision" not in unistoreOld["storeInfo"]) else unistoreOld["storeInfo"]["revision"]
	},
	"storeContent": [],
}

# Icons array
icons = []
iconIndex = 0

# Make 3DS, DSi, R4 icons
for file in os.listdir("icons"):
	if file[-3:] == "png":
		with Image.open(open(os.path.join("icons", file), "rb")) as icon:
			if not os.path.exists(os.path.join("icons", "temp")):
				os.mkdir(os.path.join("icons", "temp"))

			icon.thumbnail((48, 48))
			icon.save(os.path.join("icons", "temp", str(iconIndex) + ".png"))
			icons.append(str(iconIndex) + ".png")
			iconIndex += 1

# Auth header
header = None
if len(sys.argv) > 1:
	header = {"Authorization": f"token {sys.argv[1]}"}

# Get path files
sets = [f for f in glob.glob("sets/*/*")]

# Generate UniStore entries
for path in sets:
	info = {}

	setName = path[path.rfind(os.path.sep)+1:]

	updated = datetime.datetime.utcfromtimestamp(int("0" + git.Repo(".").git.log(["-n1", "--pretty=format:%ct", "--", path.replace("\\", "/") + f"/{setName}.t3x"])))
	created = datetime.datetime.utcfromtimestamp(int("0" + git.Repo(".").git.log(["--pretty=format:%ct", "--", path.replace("\\", "/") + f"/{setName}.t3x"]).split("\n")[-1]))

	with open(os.path.join(path, "info.json")) as file:
		info = json.load(file)

	screenshots = []
	if os.path.exists(os.path.join(path, "screenshots")):
		dirlist = os.listdir((os.path.join(path, "screenshots")))
		dirlist.sort()
		for screenshot in dirlist:
			if screenshot[-3:] == "png":
				screenshots.append({
					"url": f"https://raw.githubusercontent.com/Universal-Team/ut-game-sets/main/{path}/screenshots/{screenshot}",
					"description": screenshot[:screenshot.rfind(".")].capitalize().replace("-", " ")
				})

	setInfo = {
		"title": info["title"] if "title" in info else setName,
		"version": info["version"] if "version" in info else "v1.0.0",
		"author": info["author"] if "author" in info else "",
		"category": info["categories"] if "categories" in info else [],
		"console": getName(path),
		"icon_index": getDefaultIcon(path),
		"description": info["description"] if "description" in info else "",
		"screenshots": screenshots,
		"license": info["license"] if "license" in info else "",
		"last_updated": updated.strftime("%Y-%m-%d at %H:%M (UTC)")
	}

	if "amount" in info:
  		setInfo["amount"] = info["amount"]

	if not "unistore_exclude" in info or info["unistore_exclude"] == False:
		# Make icon for UniStore
		if os.path.exists(os.path.join(path, "icon.png")):
			with Image.open(open(os.path.join(path, "icon.png"), "rb")) as icon:
				if not os.path.exists(os.path.join("icons", "temp")):
					os.mkdir(os.path.join("icons", "temp"))

				icon.thumbnail((48, 48))
				icon.save(os.path.join("icons", "temp", str(iconIndex) + ".png"))
				icons.append(str(iconIndex) + ".png")
				setInfo["icon_index"] = iconIndex
				iconIndex += 1

		# Add entry to UniStore
		unistore["storeContent"].append({
			"info": setInfo,
			info["title"] if "title" in info else setName: [
				{
					"type": "downloadFile",
					"file": f"https://raw.githubusercontent.com/Universal-Team/ut-game-sets/main/{urllib.parse.quote(path)}/{urllib.parse.quote(setName)}.t3x",
					"output": f"sdmc:/3ds/ut-games/sets/{getName(path)}/{setName}.t3x",
					"message": f"Downloading {info['title'] if 'title' in info else setName}..."
				}
			]
		})

	# Website file
	web = setInfo.copy()
	web["layout"] = "app"
	web["created"] = created.strftime("%Y-%m-%dT%H:%M:%SZ")
	web["updated"] = updated.strftime("%Y-%m-%dT%H:%M:%SZ")
	web["systems"] = [web["console"]]
	web["downloads"] = {f"{setName}.t3x": {
		"url": f"https://raw.githubusercontent.com/Universal-Team/ut-game-sets/main/{urllib.parse.quote(path)}/{setName}.t3x",
		"size": os.path.getsize(os.path.join(path, f"{setName}.t3x"))
		}}
	if web["icon_index"] < len(sections):
		web["icon"] = f"https://raw.githubusercontent.com/Universal-Team/ut-game-sets/main/icons/{getSection(path)}.png"
	else:
		web["icon"] = f"https://raw.githubusercontent.com/Universal-Team/ut-game-sets/main/{urllib.parse.quote(path)}/icon.png"
	web["image"] = web["icon"]
	web.pop("icon_index")
	if "title" in web:
		if not os.path.exists(os.path.join("docs", "_" + webName(web["console"]))):
			os.mkdir(os.path.join("docs", "_" + webName(web["console"])))
		with open(os.path.join("docs", "_" + webName(web["console"]), webName(web["title"]) + ".md"), "w", encoding="utf8") as file:
			file.write("---\n" + yaml.dump(web) + "---\n")

	for category in web["category"]:
		if not os.path.exists(os.path.join("docs", webName(web["console"]), "category")):
			os.makedirs(os.path.join("docs", webName(web["console"]), "category"))
		with open(os.path.join("docs", webName(web["console"]), "category", category + ".md"), "w", encoding="utf8") as file:
			file.write(f"---\nlayout: cards\ntitle: {getName(path)} - {category}\nsystem: {webName(web['console'])}\ncategory: {category}\n---\n")

# Make t3x
with open(os.path.join("icons", "temp", "icons.t3s"), "w", encoding="utf8") as file:
	file.write("--atlas -f rgba -z auto\n\n")
	for icon in icons:
		file.write(icon + "\n")
os.system(f"tex3ds -i {os.path.join('icons', 'temp', 'icons.t3s')} -o {os.path.join('docs', 'unistore', 'ut-game-sets.t3x')}")

# Increment revision if not the same
if unistore != unistoreOld:
	unistore["storeInfo"]["revision"] += 1

# Write unistore to file
with open(os.path.join("docs", "unistore", "ut-game-sets.unistore"), "w", encoding="utf8") as file:
	file.write(json.dumps(unistore, sort_keys=True))
