#This code file performs the data pull from TBA

import concurrent.futures as cf
from requests_futures.sessions import FuturesSession
import mysql.connector
import json
import re
import logging
import decimal

API_KEY = '4ZhSjJb0eE1Fhkw5MJ80Dscvn8bGiFI93XQBPrzl4RtWPxJuJZZWuUYqNmoBFnDa'
BASE_URL = 'https://www.thebluealliance.com/api/v3'
scoutingdb = mysql.connector.connect(
	host='localhost',
	user='root',
	passwd='KikoTheDerpyCat',
	database='scouting2020'
)
sqlsession = FuturesSession()
sqlsession.headers.update({'X-TBA-Auth-Key':API_KEY})

stdev = decimal.Decimal(58.3)

dbcursor = scoutingdb.cursor()

def eventlistPull():
	future = sqlsession.get(BASE_URL + '/events/2020/simple')
	reply = future.result()
	eventlist = json.loads(reply.content)
	sql = "insert into eventlist (eventkey, lastmodified) values (%s, %s)"
	vals = list()
	futures = list()
	for x in eventlist:
		eventfuture = sqlsession.get(BASE_URL + '/event/' + x['key'] + '/matches/simple')
		futures.append(eventfuture)
	for y in futures:
		modifiedreply = y.result()
		if modifiedreply.content['event_type'] not in (99, 100, -1):
			vals.append((eventlist[futures.index(y)]['key'], modifiedreply.headers["Last-Modified"]))
	dbcursor.executemany(sql, vals)
	scoutingdb.commit()

def matchDataPull():
	dbcursor.execute("select * from eventlist")
	eventlist = dbcursor.fetchall()
	updatedevents = 0
	futures = list()
	for x in eventlist:
		future = sqlsession.get(BASE_URL + '/event/' + x[0] + '/matches/simple', headers={'If-Modified-Since':x[1]})
		logging.debug("%s was last modified %s", x[0], x[1])
		futures.append(future)
	vals = list()
	sql = "insert into mastermatchlist (matchkey, eventkey, scheduledtime, playedtime, red1, red2, red3, blue1, blue2, blue3, redscore, bluescore, actualmargin, complevel) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) on duplicate key update playedtime=values(playedtime), redscore=values(redscore), bluescore=values(bluescore), actualmargin=values(actualmargin)"
	for future in futures:
		reply = future.result()
		if reply.status_code == 200:
			#futures.get(future):
			thiseventkey = eventlist[futures.index(future)][0]
			logging.info("updates available for event key " + thiseventkey)
			matchdata = json.loads(reply.content)
			dbcursor.execute("update eventlist set lastmodified = %s where eventkey = %s", (reply.headers['Last-Modified'], thiseventkey))
			updatedevents = updatedevents + 1
			scoutingdb.commit()
			for y in matchdata:
				vals.append((
					y["key"],
					thiseventkey,
					y["time"],
					y["actual_time"],
					int(re.sub(r"\D", "", y["alliances"]["red"]["team_keys"][0])),
					int(re.sub(r"\D", "", y["alliances"]["red"]["team_keys"][1])),
					int(re.sub(r"\D", "", y["alliances"]["red"]["team_keys"][2])),
					int(re.sub(r"\D", "", y["alliances"]["blue"]["team_keys"][0])),
					int(re.sub(r"\D", "", y["alliances"]["blue"]["team_keys"][1])),
					int(re.sub(r"\D", "", y["alliances"]["blue"]["team_keys"][2])),
					y["alliances"]["red"]["score"],
					y["alliances"]["blue"]["score"],
					y["alliances"]["red"]["score"] - y["alliances"]["blue"]["score"],
					y["comp_level"]))
		dbcursor.executemany(sql, vals)
		scoutingdb.commit()
	if updatedevents > 0:
		calcELOs()
	return updatedevents

def resetELOs():
	dbcursor.execute("select * from teamEloList")
	teamlist = dbcursor.fetchall()
	sql = "update teamEloList set currentelo = %s where teamnumber = %s"
	values = list()
	for x in teamlist:
		values.append((x[2], x[0]))
	dbcursor.executemany(sql, values)
	scoutingdb.commit()
	#re-populate all ELOs to the start-of-season values

def calcELOs():
	resetELOs()			# commented out to enable incremental calculations only.
	logging.info("Elo table reset!")
	dbcursor.execute("select matchkey, red1, red2, red3, blue1, blue2, blue3, redscore, bluescore, actualmargin, complevel from mastermatchlist order by scheduledtime")
	resultdata = dbcursor.fetchall()
	sql1 = "update teamEloList set currentelo = %s where teamnumber = %s"
	for x in resultdata:
		red1elo = lookupTeamELO(x[1]) # red1
		red2elo = lookupTeamELO(x[2]) # red2
		red3elo = lookupTeamELO(x[3]) # red3
		blue1elo = lookupTeamELO(x[4]) # blue1
		blue2elo = lookupTeamELO(x[5]) # blue2
		blue3elo = lookupTeamELO(x[6]) # blue3
		sumredelo = decimal.Decimal(red1elo + red2elo + red3elo)
		sumblueelo = decimal.Decimal(blue1elo + blue2elo + blue3elo)
		predictedredmargin = decimal.Decimal(sumredelo - sumblueelo)*decimal.Decimal(0.004)*stdev
		redwinchance = decimal.Decimal(1/(pow(10,(sumblueelo - sumredelo)/400)+1))
		kval = decimal.Decimal(12.0)
		if x[10] != 'qm': # complevel
			kval = decimal.Decimal(3.0)
		elochange = kval*decimal.Decimal(x[9] - predictedredmargin)/stdev # predictedredmargin & actualmargin
		values1 = [
			(red1elo + elochange, x[1]),
			(red2elo + elochange, x[2]),
			(red3elo + elochange, x[3]),
			(blue1elo - elochange, x[4]),
			(blue2elo - elochange, x[5]),
			(blue3elo - elochange, x[6])
		]
		if x[9] != 0:
			dbcursor.executemany(sql1,tuple(values1))
		dbcursor.execute("update mastermatchlist set predictedredmargin = %s where matchkey = %s", (predictedredmargin, x[0]))
		dbcursor.execute("update mastermatchlist set probredwins = %s where matchkey = %s", (redwinchance, x[0]))
		scoutingdb.commit()
		logging.debug("Elos updated for teams in match " + x[0] + "by change amount " + str(elochange))
	#perfrorm all elo calculations for full match list and udpate

def lookupTeamELO(teamnumber):
	dbcursor.execute("select currentelo from teamEloList where teamnumber = %s", (teamnumber,))
	teamelo = dbcursor.fetchall()
	return decimal.Decimal(teamelo[0][0])

def main():
	logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename='tba-pull.log', level=logging.INFO)
	logging.info("Started")
	eventupdates = 0
	try:
		eventupdates = matchDataPull()
	except:
		logging.exception("An error occurred while executing the script.")
	dbcursor.close()
	logging.info("Updated match data for %s events", eventupdates)
	logging.info("Finished")

	

if __name__ == "__main__":
	main()
