
# This script was written by Trevor Hubbard; its purpose is collecting the information
# necessary to create a social network of various SoundCloud artists! 

# =========================
#         SETUP
# =========================

# Here are various import statements
import soundcloud, requests, json, time, itertools, heapq, traceback
import pandas as pd
import networkx as nx
from pathlib import Path

# Here, I'm declaring the "client" variable, which I'll use throughout the rest of the application
userClientID = input("\nEnter your SoundCloud client ID: ")
client = soundcloud.Client(client_id=userClientID)

# Setting up the priority queue for the crawling fronteir; I got this code # from the Python
# docs @ https://docs.python.org/3.5/library/heapq.html#priority-queue-implementation-notes
pq = []                         
entry_finder = {}               
REMOVED = '<removed-item>'      
counter = itertools.count()
graph = nx.DiGraph()

# Checking if the user already has a graph they want to work on 
graphPath = ""
userInput = int(input("\nAre you working on a new graph, or adding to an existing one?\n\n1) New Graph\n2) Existing Graph\n\nPlease enter the number corresponding with your choice: "))
if (userInput == 2):
	graphPath = input("\nPlease enter the path to the .graphml file you're trying to expand: ")

# Declaring the cache
cache = {}

# These dictionaries are essential data structures
artistNameDict = {}
artistEncounterDict = {}
artistExploredDict = {}
fullyExplored = {}

# =========================
#          METHODS
# =========================

# This method will extract a page cursor from a SoundCloud URI
def extractCursor(uri):

	# Step through the URI backwards, looking for the "cursor" field
	for curIdx in range(len(uri), 0, -1):
		curChar = uri[curIdx-1]
		if (curChar == '='):
			return int(uri[curIdx:])

# This method will clear out any items in the cache that haven't been accessed
def clearCache():
	toDelete = []
	for key in cache.keys():
		accessCt = cache[key][0]
		if (accessCt == 0):
			toDelete.append(key)
			
	for key in toDelete:
		del cache[key]

# When given a user's ID, this method will return a list of (username, ID) pairs
# that the given user follows
def getFollowingFromID(userID):
	
	# Set up some of the variables needed for the impending search
	getRequest = '/users/' + str(userID) + '/followings'
	apiResponse = client.get(getRequest, limit=100, linked_partitioning=1)
	userList = []
	hasMore = True

	# Run the loop to pull the names of the users
	while (hasMore):
		followingList = apiResponse.fields()['collection']
		for user in followingList:
			
			attributesToGrab = ["track_count", "followers_count", "public_favorites_count", "permalink_url", "city", "country"]
			infoList = []
			for attribute in attributesToGrab:
				info = user[attribute]
				if (info is None):
					infoList.append("n/a")
				else:
					infoList.append(info)

			userList.append((user['username'], user['id'], infoList))


		# If there aren't any more pages, change hasMore to False. Otherwise, continue
		if (apiResponse.fields()['next_href'] is None):
			hasMore = False
		else:
			nextCursor = extractCursor(apiResponse.fields()['next_href'])
			apiResponse = client.get(getRequest, limit=200, linked_partitioning=1, cursor=nextCursor)

	# Return the results
	return userList

# This is a more lightweight version of the above method
def getFollowingFromID_light(userID):
	
	# Set up some of the variables needed for the impending search
	getRequest = '/users/' + str(userID) + '/followings'
	apiResponse = client.get(getRequest, limit=100, linked_partitioning=1)
	userList = {}
	hasMore = True

	# Run the loop to pull the names of the users
	while (hasMore):
		followingList = apiResponse.fields()['collection']
		for user in followingList:
			userList[user['id']] = 1

		# If there aren't any more pages, change hasMore to False. Otherwise, continue
		if (apiResponse.fields()['next_href'] is None):
			hasMore = False
		else:
			nextCursor = extractCursor(apiResponse.fields()['next_href'])
			apiResponse = client.get(getRequest, limit=200, linked_partitioning=1, cursor=nextCursor)

	# Return the results
	return userList

# This is a more lightweight version of the above method
def updateFavoritesFromID(userID, boostThreshold):
	
	# Set up some of the variables needed for the impending search
	getRequest = '/users/' + str(userID) + '/favorites'
	apiResponse = client.get(getRequest, limit=100, linked_partitioning=1)
	hasMore = True

	# Some data structures that'll limit the growth of the favoritesList
	favoriteCtDict = {}

	# Run the loop to pull the names of the users
	while (hasMore):
		favoritesList = apiResponse.fields()['collection']
		for song in favoritesList:

			# Skip artists that favorite themselves
			newUserID = song["user_id"]
			if (newUserID == userID): 
				continue
			newUserName = song["user"]["username"]

			# Check to see if you've already saturated the artistEncounterDict w/ this artist
			if (newUserID not in favoriteCtDict):
				favoriteCtDict[newUserID] = 0
			favoriteCtDict[newUserID] += 1
			if (favoriteCtDict[newUserID] > boostThreshold):
				continue

			# Update the encounter count
			if (newUserID not in artistEncounterDict):
				artistEncounterDict[newUserID] = 0
				artistNameDict[newUserID] = newUserName
			artistEncounterDict[newUserID] += 1

		# If there aren't any more pages, change hasMore to False. Otherwise, continue
		if ("next_href" not in apiResponse.fields() or apiResponse.fields()['next_href'] is None):
			hasMore = False
		else:
			nextCursor = extractCursor(apiResponse.fields()['next_href'])
			apiResponse = client.get(getRequest, limit=200, linked_partitioning=1, cursor=nextCursor)

# This method returns the following attributes for a given userID: 
# (# of tracks, # of followers, # of favorites, public URL, city, country)
def getInfoFromID(userID):

	# Create the get request and pull the info from the API
	getRequest = '/users/' + str(userID)
	apiResponse = client.get(getRequest)
	attributesToGrab = ["track_count", "followers_count", "public_favorites_count", "permalink_url", "city", "country"]
	infoList = []
	for attribute in attributesToGrab:
		info = apiResponse.fields()[attribute]
		if (info is None):
			infoList.append("n/a")
		else:
			infoList.append(info)
	return infoList

# When given the URL of a soundcloud user, this method will return that user's ID
def getArtistID(url):

	# First, parse the username out of the URL
	# https://soundcloud.com/chinatownslalom (23?)
	username = url[23:]

	# Remove the "s" from the http if it exists
	if (url.startswith("https")):
		url = url[:4] + url[5:]

	# Set up the variables needed for the search
	apiResponse = client.get('/users/', q=username)

	for response in apiResponse:
		curURL = (response.fields()["permalink_url"])
		# Remove the "s" from the http if it exists
		if (curURL.startswith("https")):
			curURL = curURL[:4] + curURL[5:]
		if (url == curURL):
			return (response.fields()["username"], response.fields()["id"])

# This method checks if the target follows the source back
def followBack(source, target):

	print("Checking to see if %s is following %s..." % (target[1], source[1]))

	# First, check to see if the target has been cached
	if (target[0] in cache):

		# Grab the list of following from the cache
		print("We found %s in the cache! Continuing to check..." % target[1])
		followingList = cache[target[0]][1]

		# If the source *is* in the query list, return True and delete from cache
		if (source[0] in followingList):
			del cache[target[0]]
			print("YES")
			return True

		# Otherwise, update accessCt and then return False
		else:
			cache[target[0]][0] += 1
			print("NO")
			return False

	# If the target hasn't been cached, request the API and add it to the cache
	else:
		# Surrounding the API call with a try/except in case it fails
		try:
			targetFollowing = getFollowingFromID_light(target[0])
		except Exception as e:
			if isinstance(e, KeyboardInterrupt):
				sys.exit()
			print("*** ERROR: FAILED TO GRAB TARGET ARTIST'S FOLLOWING; TRYING AGAIN ***")
			return followBack(source, target)
		cache[target[0]] = [0, targetFollowing]
		if (source[0] in targetFollowing):
			print("YES\n")
			# Surrounding the API call with a try/except in case it fails
			try:
				updateFavoritesFromID(target[0], 3)
			except Exception as e:
				print("*** ERROR: SOMETHING FAILED WHEN UPDATING PRIORITY RE: FAVORITES ***")
				traceback.print_exc()
			return True
		else:
			print("NO\n") 
			return False

# This is a priority queue method to add an item to the queue
def pqAdd(item, priority):
	priority = priority * -1
	if item in entry_finder:
		pqRemove(item)
	count = next(counter)
	entry = [priority, count, item]
	entry_finder[item] = entry
	heapq.heappush(pq, entry)

# This is a priority queue method; it'll pop an item from the queue
def pqPop():
	while pq:
		priority, count, item = heapq.heappop(pq)
		# If the item hasn't already been removed...
		if item is not REMOVED:
			del entry_finder[item]
			return (item, priority)
	# Return False if the queue is empty
	return False

# This is a priority queue helper method; it removes an item from the queue 
def pqRemove(item):
	entry = entry_finder.pop(item)
	entry[-1] = REMOVED

# This is a priority queue method; it'll print out the top 10 items in the priority queue
def pqPrintTop():

	# Creating a dictionary w/ priorties as keys and items as indices
	priorityDict = {}
	for item in pq:
		curPriority = item[0]
		curID = item[2]
		if (curID is not REMOVED):
			if (curPriority not in priorityDict):
				priorityDict[curPriority] = []
			priorityDict[curPriority].append((item[1], curID))

	# Create the sorted list of the top ten
	remaining = 50
	sortedList = []
	for curPriority, curList in sorted(priorityDict.items()):
		done = False
		for curItem in curList:
			sortedList.append((curPriority, curItem[1]))
			remaining -= 1
			if (remaining == 0):
				done = True
				break
		if (done): break

	# Print the list
	for item in sortedList:
		print("- %s (ID: %s; Priority: %s)" % (artistNameDict[item[1]], item[1], item[0]))
	print("\n")


# =========================
#           MAIN 
# =========================

# These declarations help to setup the data collection loop by adding a starting point to the priority queue
leftTillWrite = 2
leftTillCacheClear = 3
backupCt = 0
oldSeeds = []
newGraph = True

# Here, we read through the graph in the file to load its information
if (graphPath != ""):

	# Update the graph to be the one we've already created
	newGraph = False
	graph = nx.read_graphml(graphPath)
	print("Updating data structures from graph...")

	# Iterate through each node currently in the graph
	for node, data in graph.nodes(data=True):

		if ('id' not in data):
			continue

		# Add the artist's information to the artistNameDict
		artistNameDict[data['id']] = node

		# If a node has the explored tag, mark it as explored
		if (data["explored"] == 1):
			artistExploredDict[data['id']] = 1
			oldSeeds.append(data['id'])
		
	print(artistEncounterDict)
	curSeedIdx = 0
	while(not artistEncounterDict):
		updateFavoritesFromID(oldSeeds[curSeedIdx], 100)
		curSeedIdx += 1
	print()
	print(artistEncounterDict)
	for curArtist in artistEncounterDict.keys():
		if (curArtist in oldSeeds):
			continue
		pqAdd(curArtist, artistEncounterDict[curArtist])

# Otherwise, if the graph is empty, start this way: 
else:
	startingPoint = getArtistID(input("\nEnter the SoundCloud URL of your starting point: ").strip()) 
	graphPath = startingPoint[0] + ".graphml"
	artistNameDict[startingPoint[1]] = startingPoint[0]
	artistEncounterDict[startingPoint[1]] = 1
	pqAdd(startingPoint[1], 1)

# Here, we check if there are any backups
if (Path("backups").exists()):
	for child in Path("backups").iterdir():
		backupCt += 1

# Grab the first artist seed
curSeed, curPriority = pqPop()
firstRun = True
followerThreshold = 0

# While the priority queue isn't empty, continue the data collection
while (not isinstance(curSeed, bool)):

	shuffledArtists = {}

	# Surrounding the API call with a try/except in case it fails
	try:
		seedArtistInfo = getInfoFromID(curSeed)
	except:
		print("*** ERROR: FAILED TO GRAB SEED ARTIST INFO; TRYING AGAIN ***")
		continue

	if (firstRun):
		firstRun = False
		if (newGraph):
			followerThreshold = int(seedArtistInfo[1])
		else:
			# Surrounding the API call with a try/except in case it fails
			try:
				firstArtistInfo = getInfoFromID(oldSeeds[0])
				followerThreshold = int(firstArtistInfo[1])
			except:
				print("*** ERROR: FAILED TO GRAB THE SEED ARTIST INFO FROM THE FIRST ARTIST; USING THE NEW ONE ***")
				followerThreshold = int(seedArtistInfo[1])

		# Move onto a new seed if this one is not up to scuff
		if (seedArtistInfo[1] > followerThreshold and curSeed not in shuffledArtists):
			print("%s is above the followerThreshold, so moving onto a new seed" % artistNameDict[curSeed])
			shuffledArtists[curSeed] = 1
			pqAdd(curSeed, curPriority * -.02)
			curSeed, curPriority = pqPop()
			continue

	# Surrounding the API call with a try/except in case it fails
	try:
		# Grab the current seed artist's following list, and iterate through it
		following = getFollowingFromID(curSeed)
	except:
		print("*** ERROR: FAILED TO GRAB SEED ARTIST'S FOLLOWING LIST; TRYING AGAIN ***")
		continue

	# Marked the current seed artist as explored, and add a node in the graph for it
	artistExploredDict[curSeed] = 1
	seedArtistName = artistNameDict[curSeed]
	oldSeeds.append(curSeed)

	graph.add_node(seedArtistName, id=curSeed, trackCt=seedArtistInfo[0], followerCt=seedArtistInfo[1], favoriteCt=seedArtistInfo[2], url=seedArtistInfo[3], city=seedArtistInfo[4], country=seedArtistInfo[5], explored=1)

	# Print some information so that you know it's been explored
	print("\n\n\nExploring %s (ID: %s)" % (seedArtistName, curSeed))
	leftTillPriorityPrint = 1
	
	for idx, toUnpack in enumerate(following):

		# Printing the priority queue every 10 artists
		leftTillPriorityPrint -= 1
		if (leftTillPriorityPrint == 0):
			print("\nThe priority queue looks like:\n")
			pqPrintTop()
			leftTillPriorityPrint = 10

		newArtist, newID, newInfo = toUnpack

		print("We found %s (ID: %s) (%d/%d)" % (newArtist, newID, idx, len(following)))

		# Add an edge back to the artist if you've already seen them
		if (newID in artistExploredDict): 
			graph.add_edge(seedArtistName, newArtist)
			continue

		# Skip an artist if they don't follow the seed artist back
		if (not followBack((curSeed, seedArtistName), (newID, newArtist))): 
			continue

		# Add the new artist's name to the nameDict, update their encounter count, 
		# and add them to the graph and priority queue
		artistNameDict[newID] = newArtist 
		if (newID not in artistEncounterDict):
			artistEncounterDict[newID] = 0
		artistEncounterDict[newID] += 1
		pqAdd(newID, artistEncounterDict[newID])
		graph.add_node(newArtist, id=newID, trackCt=newInfo[0], followerCt=newInfo[1], favoriteCt=newInfo[2], url=newInfo[3], city=newInfo[4], country=newInfo[5], explored=0)
		graph.add_edge(seedArtistName, newArtist)

	# Write to disk if 10 new artists have been processed
	if (leftTillWrite == 0):
		leftTillWrite = 1
		print("\nWriting to disk!")
		curTime = time.time()
		nx.write_graphml(graph, graphPath)
		timeToWrite = time.time() - curTime
		print("It took %.3f seconds to write that to disk\n" % timeToWrite)

	# Clear the cache if 3 new artists have been processed
	if (leftTillCacheClear == 0):
		print("Clearing cache...\n")
		clearCache()

	# Sleep to not overload the SoundCloud API
	time.sleep(0.3)

	# Update the current artist seed, and save the current graph
	curSeed, curPriority = pqPop()
	toAddBack = []
	toDeleteFromSeeds = []
	stillSearching = True
	nextArtist = False

	# Make sure that the artists you're choosing to follow actually follow you back
	for seedIdx, oldSeed in enumerate(oldSeeds):
		if (not stillSearching): break
		while (stillSearching):
			if (nextArtist):
				nextArtist = False
				break
			curSeedPackage = (curSeed, artistNameDict[curSeed])
			oldSeedPackage = (oldSeed, artistNameDict[oldSeed])
			if (followBack(curSeedPackage, oldSeedPackage) and followBack(oldSeedPackage, curSeedPackage)):
				print("Found a match: %s and %s were following each other" % (artistNameDict[curSeed], artistNameDict[oldSeed]))

				# THIS IS WHERE I SHOULD ADD INFORMATION ABOUT RESHUFFLING
				if (curSeed not in shuffledArtists):
					# Check if their follower count is above the threshold
					try:
						seedArtistInfo = getInfoFromID(curSeed)
						if (seedArtistInfo[1] > followerThreshold):
							shuffledArtists[curSeed] = 1
							toAddBack.append((curSeed, int(curPriority * -0.1)))
							print("%s had %d followers, but the threshold was %d. Adding them back into the queue w/ the priority %d." % (artistNameDict[curSeed], seedArtistInfo[1], followerThreshold, int(curPriority * -0.5)))
							for pair in toAddBack:
								newPriority = int(pair[1] * -0.2)
								if (newPriority == 0):
									newPriority += 1
								pqAdd(pair[0], newPriority)
								print("Added back %s w/ the priority %s" % (str(pair[0]), str(newPriority)))
								if (pair[0] in artistNameDict):
									print("(The artist's name was %s" % artistNameDict[pair[0]])
							toAddBack = []
						else:
							stillSearching = False
							break
					except:
						print("*** ERROR: FAILED TO GRAB SEED ARTIST INFO; JUST ROLLING W/ THAT AS A SEED ***")
						stillSearching = False
						break
						
				else:
					stillSearching = False
					break
			else:
				print("Didn't find a match; %s and %s weren't following eachother" % (artistNameDict[curSeed], artistNameDict[oldSeed]))
				toAddBack.append((curSeed, curPriority))
			if (stillSearching):
				popped = pqPop()
				if (isinstance(popped, bool)):
					print("\n\n\nADDING %s TO BE REMOVED FROM OLDSEEDS\n\n\n" % artistNameDict[oldSeed])
					toDeleteFromSeeds.append(oldSeed)
					nextArtist = True
					if (seedIdx == len(oldSeeds)-1):
						stillSearching = False
					for pair in toAddBack:
						newPriority = int(pair[1] * -0.2)
						if (newPriority == 0):
							newPriority += 1
						pqAdd(pair[0], newPriority)
						print("Added back %s w/ the priority %s" % (str(pair[0]), str(newPriority)))
						if (pair[0] in artistNameDict):
							print("(The artist's name was %s" % artistNameDict[pair[0]])
					toAddBack = []
					curSeed, curPriority = pqPop()
					continue	
				else:
					curSeed, curPriority = popped
		for pair in toAddBack:
			newPriority = int(pair[1] * -0.2)
			if (newPriority == 0):
				newPriority += 1
			pqAdd(pair[0], newPriority)
			print("Added back %s w/ the priority %s" % (str(pair[0]), str(newPriority)))
			if (pair[0] in artistNameDict):
				print("(The artist's name was %s" % artistNameDict[pair[0]])
		toAddBack = []

	# Clearing out any artists we've fully explored from the old seeds list
	for seedToDelete in toDeleteFromSeeds:
		print("\n\n\n\n**** REMOVING %s FROM OLDSEEDS****\n\n\n" % artistNameDict[seedToDelete])
		oldSeeds.remove(seedToDelete)

	leftTillWrite -= 1
	leftTillBackup -= 1
	leftTillCacheClear -= 1


