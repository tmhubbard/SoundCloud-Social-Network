
# This script was written by Trevor Hubbard; its purpose is merging together multiple graphs
# that were created with my SoundCloud social network generator


# =========================
#         SETUP
# =========================

# Here are various import statements
import networkx as nx
from pathlib import Path


# =========================
#          METHODS
# =========================

# This method will merge together two networkx graphs
def mergeGraphPair(G1, G2):

	# Here, you check if the graph has been relabeled; if not, convert the IDs of the nodes to their SoundCloud IDs, 
	# and store their names in another parameter. You can also mark G1's explored tracks
	graphArray = [G1, G2]
	G1_exploredDict = {}
	hasBeenRelabled = [False, False]
	for graphIdx, curGraph in enumerate(graphArray):

		# In this inner for loop, you'll want to create a dict of (username, ID) pairs,
		# so you can then run the nx.relabel_nodes() method to change the graph's IDs
		labelMapping = {}
		for curLabel, data in curGraph.nodes(data=True):

			# Skip any bad nodes
			if (not data):
				continue

			# If the current graph is G1, then mark any explored users in G1_exploredDict
			if (graphIdx == 0):
				
				if (data['explored'] == 1):
					G1_exploredDict[data['id']] = 1

			# Check if the graph has been relabeled or not
			if ('relabled' not in data):
				labelMapping[curLabel] = data['id']
				data['username'] = curLabel
				data['relabled'] = 1
			else:
				hasBeenRelabled[graphIdx] = True

		# Relabel the graphs if they haven't been already
		if (not hasBeenRelabled[graphIdx]):
			print("G%s has not been relabled! Relabeling it now..." % str(graphIdx+1))
			graphArray[graphIdx] = nx.relabel_nodes(curGraph, labelMapping)

	# Update the graphs to point to their relabeled counterparts
	G1 = graphArray[0]
	G2 = graphArray[1]

	# Create the composed graph, and then fix all of the "explored" tags
	G_composed = nx.compose(G1, G2)
	for node, data in G_composed.nodes(data=True):

		# Skip any bad nodes
		if (not data):
			continue
		
		if (data['explored'] == 0 and node in G1_exploredDict):
			data['explored'] = 1

	# Return the newly composed graph
	return G_composed
	

# This recursive method will merge together an array of graphs
def mergeGraphArray(graphArray):

	# Break statement for the recursion
	if (len(graphArray) == 1):
		return graphArray[0]

	# Recursive portion of the method; merge together the first two graphs, and then 
	# return the array containing the merged graph and graphArray[2:]
	else:
		newGraphArray_p1 = [mergeGraphPair(graphArray[0], graphArray[1])]
		newGraphArray_p2 = graphArray[2:]
		print((newGraphArray_p1))
		print((newGraphArray_p2))
		newGraphArray = newGraphArray_p1 + newGraphArray_p2
		print(newGraphArray)
		if (len(newGraphArray_p2) == 0):
			newGraphArray = [newGraphArray[0]]
		return mergeGraphArray(newGraphArray)


# =========================
#           MAIN 
# =========================

# First, I'll prompt the user to enter the paths as a comma separated list, and load them into networkx graphs
graphPathArray = [Path(x) for x in input("Enter a comma-separated list of paths for the graphs you're merging: ").split(",")]
graphArray = []
for graphPath in graphPathArray:
	graphArray.append(nx.read_graphml(graphPath))

# Now, I'll run mergeGraphArray on the graphs, ask the user for a resultPath, and write the graph! 
print(len(graphArray))
mergedGraph = mergeGraphArray(graphArray)
savePath = Path(input("Enter a title for the merged .graphml: ") + ".graphml")
nx.write_graphml(mergedGraph, savePath)