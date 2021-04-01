# SoundCloud Social Network
This pair of scripts is meant to help build “co-follower” graphs from particular artists on SoundCloud! I had the idea when thinking about some of the more niche musicians I listen to, who tend to exist in smaller subcommunities on websites like SoundCloud. I figured that I could find more musicians in their circle if I created a “co-follower network”: 

* Nodes in the graph represent musicians on SoundCloud
* Edges in the graph represent a following on SoundCloud 
	- Example: Artist A’s and Artist B’s nodes are connected if they follow each other on Soundcloud

![zoomed-out visualization of social network](https://i.imgur.com/9oMYxPd.png)
*A zoomed-out version of the SoundCloud graph I built in order to analyze the network of [Brockhamtpon] (https://en.wikipedia.org/wiki/Brockhampton_(band)) * 

![zoomed-in visualization of social network](https://i.imgur.com/HI6ABmE.png)
*A zoomed-in version of the same Brockhampton graph *

## How to Install

Download this GitHub repo, navigate to the directory you saved it to, and type: 

`pip install -r requirements.txt`

This will install the required libraries: soundcloud (for scraping the website), pandas (for data manipulation), and networkx (for creating the graph.)  

After installing the required Python libraries, you also ought to install [Gephi](https://gephi.org/). The graphs that are created are .graphml files, which are viewable in that program. 

## How to Use

Navigate to the directory you’ve saved the repo to. I’ve got separate instructions for both scripts below: 

#### networkGenerator.py

Run the following command: 

`python networkGenerator.py`

This will launch the script! This was made for a quick turnaround research interest of mine, so things from here on in are a little inelegant. Here’s what the program looks like: 

![screenshot of code](https://i.imgur.com/yKUspkJ.png)

You’ll need to enter a SoundCloud client ID in order to scrape SoundCloud. You can register for a SoundCloud API key [here] (https://soundcloud.com/you/apps). (Once you have one, you could always hard-code this into the Python script once you’ve gotten one.) After that, you can type “1” to start a new graph. (If you typed “2” for “Existing Graph”, it’ll just ask you to enter the path of the graphml file.) Finally, you need to enter a SoundCloud profile URL as a beginning seed for the network - once you do that, the program will start running! It pipes the data it’s scraping from SoundCloud directly into the .graphml file – it’ll write to disk every time it finishes fully “processing” an artist. 


After several attempts with scraping strategies, I settled on a priority-queue based strategy for deciding how to scrape the “next artist” after the initial seed artist. The script scrape’s the seed artist’s “Following” list, and then iterates through to understand whether there’s a mutual following. Once that’s finished, the script decides where next to scrape through a heuristic combining the “number of times a particular artist was seen in other artists’ ‘Following’ List” and “number of times that artist appeared on seed artists’ Favorite songs list.” 


The script attempts to reduce the overhead of “scraping time” by caching follower lists it sees; in order to reduce memory overhead, this cache is cleared each time the script scrapes leftTillCacheClear artists (set to 3 by default). Every time the script scrapes leftTillWrite artists (set to 2 by default), it’ll save a .graphml file in the same directory. This’ll be named “[initial seed artist].graphml”. Since I was trying to see how large the graphs might get, there’s no “stop condition” – the scripts will continue to scrape until you stop them manually, with a CTRL+C command. 

#### mergeGraphs.py
This script will merge together a couple of .graphml files – it’s useful for making larger graphs! (To make the previously shown Brockhampton graph, I individually scraped networks for each of the group members.) 

In order to start the script, run the following command: 

`pthon mergeGraphs.py`

The script will ask you to enter a list of comma-separated paths to the .graphml files you’re trying to merge. Once you do that, it’ll merge the graphs, and ask you to input a title for the graph; it’ll save the resulting graph in the same directory.  
