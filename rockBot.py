# -*- coding: utf-8 -*-
"""
Created on Sat Jun 23 11:54:29 2018

@author: oxrock
"""

import sc2
import math
import time
#from sentBot import SentdeBot
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.bot_ai import*
import random
from sc2.helpers import ControlGroup
from sc2.constants import COMMANDCENTER, SCV,SUPPLYDEPOT,REFINERY, BARRACKS, MARINE,BARRACKSTECHLAB,BARRACKSREACTOR,\
MARAUDER,LIFT_BARRACKS,LAND_BARRACKS,BARRACKSFLYING,ENGINEERINGBAY,ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1,\
ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2,ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3,RESEARCH_COMBATSHIELD,\
ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1,ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2,RESEARCH_CONCUSSIVESHELLS,\
ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3,ARMORY,FACTORY,ATTACK_ATTACKTOWARDS,PATROL,SCAN_MOVE,RALLY_UNITS

class rockBot(sc2.BotAI):
    def __init__(self):
        self.expansionIndex = 0
        self.expansions = []
        self.scout = None
        self.scoutGroup = None
        self.scoutTag = None
        self.elapsedTime = 0
        self.movingUnits = []
        self.rallyPoint = None
        self.trainUnits = True
        self.stepCount = 0
        self.flyingBarracks = [] #should include lists of unit,destination,iterator
        self.attacking = False
        self.recalled = True
        self.upgradesIndex = 0
        self.techUpgradesIndex = 0
        self.engineeringUpgrades = [ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1,ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1,
                                    ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2,ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2,
                                    ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3,ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3]
        
        self.techUpgrades = [RESEARCH_COMBATSHIELD,RESEARCH_CONCUSSIVESHELLS]
    
    async def on_step(self,iteration):
        self.stepCount +=1
        if self.stepCount %2 == 0:
            self.findGameTime()
            await self.manage_supply()
            await self.build_workers()
            await self.manage_expansion()
            await self.manage_refineries()
            await self.build_army_buildings()
        else:
            
            await self.build_army()
            await self.manage_army()
            await self.upgrade_army_buildings()
            await self.upgrader()
            
        if self.stepCount == 10:
            await self.releaseMovingUnits()
            await self.distribute_workers()
            await self.flyingHandler()
            await self.scouting()
            self.stepCount = 0
        
    async def scouting(self):
        if (self.elapsedTime /60) > 4:
            marines = self.units(MARINE).ready
            if marines:
                if len(marines) > 5:
                    if not self.scoutTag:
                        self.scoutTag = marines[0].tag
                        self.scout = marines[0]
                        self.expansions = []
                        for each in self.expansion_locations:
                            self.expansions.append(each)
                    
                    self.scout = self.units.find_by_tag(self.scoutTag)
                    if not self.scout:
                        self.scout = marines[0]
                        self.scoutTag = self.scout.tag
                        if self.expansionIndex+1 < len(self.expansions):
                            self.expansionIndex+=1
                        else:
                            self.expansionIndex = 0
                        
                    if self.findDistanceBetweenPositions(self.scout.position,self.expansions[self.expansionIndex]) < 5:
                        if self.expansionIndex+1 < len(self.expansions):
                            self.expansionIndex +=1
                            await self.do(self.scout.move(self.expansions[self.expansionIndex]))
                            
                        else:
                            self.expansionIndex = 0
                            await self.do(self.scout.move(self.expansions[self.expansionIndex]))
                    else:
                        await self.do(self.scout.move(self.expansions[self.expansionIndex]))
                        
                        
        
            
    async def upgrader(self):
        if len(self.units(BARRACKS)) > 1:
            if len(self.units(ENGINEERINGBAY))< 1:
                if self.can_afford(ENGINEERINGBAY):
                    if not self.already_pending(ENGINEERINGBAY):
                        await self.build(ENGINEERINGBAY, near = self.units(COMMANDCENTER)[0])
                    
            else:
                '''
                if self.upgradesIndex >1:
                    if len(self.units(ARMORY)) < 1:
                        if not self.already_pending(ARMORY):
                            if not self.units(FACTORY).exists:
                                if not self.already_pending(FACTORY):
                                    if self.can_afford(FACTORY):
                                        await self.build(FACTORY, near = self.units(COMMANDCENTER)[0])
                            else:
                                if self.can_afford(ARMORY):
                                    await self.build(ARMORY, near = self.units(COMMANDCENTER)[0])
                                    '''
                # only does first 2 engineering upgrades unless you uncomment above code               
                if self.elapsedTime/120 > self.upgradesIndex:
                    for EB in self.units(ENGINEERINGBAY).ready.noqueue:
                        if self.upgradesIndex < len(self.engineeringUpgrades):
                            if self.can_afford(self.engineeringUpgrades[self.upgradesIndex]):
                                await self.do(EB(self.engineeringUpgrades[self.upgradesIndex]))
                                self.upgradesIndex+=1
                
                if self.elapsedTime/120 > self.techUpgradesIndex:
                    for TL in self.units(BARRACKSTECHLAB).ready.noqueue:
                        if self.techUpgradesIndex  < len(self.techUpgrades):
                            if self.can_afford(self.techUpgrades[self.techUpgradesIndex]):
                                await self.do(TL(self.techUpgrades[self.techUpgradesIndex]))
                                #print(self.techUpgrades[self.techUpgradesIndex])
                                self.techUpgradesIndex+=1
                        
                
            
    
    async def flyingHandler(self):
        removalList = []
        for each in self.units(BARRACKSFLYING).ready.noqueue:
            if not self.customListSearch(each,self.flyingBarracks,0):
                await self.ammendFlyingList(each)
        for fb in self.flyingBarracks:
            await self.do(fb[0](LAND_BARRACKS,fb[1]))
            removalList.append(fb)
        self.flyingBarracks = [x for x in self.flyingBarracks if self.customListSearch(x,removalList,0) and x[0].is_flying]
                    
    def customListSearch(self,unitToFind,_list,index):
        for i in _list:
            if i == _list[index]:
                return True
        return False
        
    def findGameTime(self):
        self.elapsedTime = self.state.game_loop*0.725*(1/16)
        
    async def releaseMovingUnits(self):
        unitsMoved = []
        unitsMoving = []
        
        for each in self.movingUnits:
            x = (self.units.find_by_tag(each[0]),each[1])
            if x[0]:
                unitsMoving.append(x)
        
        for unit in unitsMoving:
            if self.findDistanceBetweenPositions(unit[0].position,unit[1]) < 5:
                unitsMoved.append(unit)
                await self.do(unit[0].stop())
        
        self.movingUnits = [x for x in unitsMoving if x not in unitsMoved]
                
        #self.movingUnits = [x for x in self.movingUnits if x not in unitsMoved and x[0]!=None]
        
    def findDistanceBetweenPositions(self,position1,position2):
        return math.sqrt(((position1[0]-position2[0])**2)+((position1[1]-position2[1])**2))
    
    def findClosestInList(self,unit,targets,shootFlying):
        closest = math.inf
        closest_target = None
        for t in targets:
            if shootFlying:
                distance = math.sqrt(((unit.position[0]-t.position[0])**2)+((unit.position[1]-t.position[1])**2))
                if distance < closest:
                    closest = distance
                    closest_target = t
            else:
                if not t.is_flying:
                    distance = math.sqrt(((unit.position[0]-t.position[0])**2)+((unit.position[1]-t.position[1])**2))
                    if distance < closest:
                        closest = distance
                        closest_target = t
        return closest_target
    
    def findTarget(self,unit, shootFlying = True):
        if len(self.known_enemy_units) > 0:
            return self.findClosestInList(unit,self.known_enemy_units,shootFlying)
        elif len(self.known_enemy_structures) > 0:
            return self.findClosestInList(unit,self.known_enemy_structures,shootFlying)
        else:
            return self.enemy_start_locations[0]
        
    async def build_army_buildings(self):
        if len(self.units(BARRACKS)+self.units(BARRACKSFLYING)) < self.elapsedTime/120: 
            if(not self.already_pending(BARRACKS)):
                if self.can_afford(BARRACKS):
                    await self.build(BARRACKS, near = random.choice(self.units(COMMANDCENTER)))
                    
    
                    
    async def ammendFlyingList(self,rax):
        destination = await self.modified_find_placement(COMMANDCENTER, near =rax.position,max_distance = 100)
        if destination != None:
            self.flyingBarracks.append([rax,destination,0])
            await self.do(rax.move(destination))
                        
    async def upgrade_army_buildings(self):
        techlabs = len(self.units(BARRACKSTECHLAB))
        reactors = len(self.units(BARRACKSREACTOR))
        
        for b in self.units(BARRACKS).ready.noqueue:
            if not b.has_add_on:
                if not b.is_flying:
                    if reactors > techlabs:
                        if self.can_afford(BARRACKSTECHLAB):
                           await self.do(b.build(BARRACKSTECHLAB))
                           if not b.has_add_on:
                                await self.do(b(LIFT_BARRACKS))
                                await self.ammendFlyingList(b)
                        
                    else:
                        if self.can_afford(BARRACKSREACTOR):
                            await self.do(b.build(BARRACKSREACTOR))
                            if not b.has_add_on:
                                #await self.ammendFlyingList(b)
                                await self.do(b(LIFT_BARRACKS))
                                if not b.has_add_on:
                                    await self.do(b(LIFT_BARRACKS))
                                    await self.ammendFlyingList(b)
                    
    async def build_army(self):
        techTags = []
        reactorTags = []
        if self.trainUnits:
            for techlab in self.units(BARRACKSTECHLAB).ready:
                techTags.append(techlab.tag)
            for reactor in self.units(BARRACKSREACTOR).ready:
                reactorTags.append(reactor.tag)
                
            for barracks in self.units(BARRACKS).ready:
                if barracks.has_add_on:
                    if barracks.add_on_tag in reactorTags:
                            if self.can_afford(MARINE):
                                if len(barracks.orders) < 2:
                                    await self.do(barracks.train(MARINE))
                                    
                    elif barracks.add_on_tag in techTags:
                        if barracks.noqueue:
                            if self.can_afford(MARAUDER):
                                await self.do(barracks.train(MARAUDER))
                
                await self.do(barracks(RALLY_UNITS,self.rallyPoint))
                    
        
           
    def findVisibleEnemies(self):
        return [x for x in self.known_enemy_units if x.is_visible]
          
    async def manage_army(self):
        marauders = self.units(MARAUDER)
        marines = self.units(MARINE)
        if self.scout in marines:
            marines.remove(self.scout)
        if not self.rallyPoint:
            self.rallyPoint = self.units(COMMANDCENTER)[0].position  #self.main_base_ramp.top_center
        if (len(marauders+marines) >25 and len(marauders+marines) > math.floor(self.elapsedTime/20)) or len(marauders+marines) > 50:
            if len(self.movingUnits) == 0:
                self.attacking = True
                self.recalled = False
                for m in marines:
                    if m.is_idle:
                        target = self.findTarget(m,shootFlying = True)
                        if not target:
                            target = self.main_base_ramp.top_center
                        else:
                            target = target.position
                        await self.do(m.attack(target))
                for m in marauders:
                    if m.is_idle:
                        target = self.findTarget(m,shootFlying = False)
                        if not target:
                            target = self.main_base_ramp.top_center
                        else:
                            target = target.position
                        await self.do(m.attack(target))
            
        else:
            if self.attacking:
                if len(marauders+marines) < (self.elapsedTime/30)*.66:
                    self.attacking = False
                    if not self.recalled:
                        for m in marines+marauders:
                            await self.do(m.move(self.rallyPoint))
                            self.movingUnits.append((m.tag,self.rallyPoint))
                            
                        self.recalled = True
                        print("Retreating with {}/{} military units remaining".format(str(len(marines+marauders)),str(math.floor(self.elapsedTime/20))))
                else:
                    for m in marines:
                        if m.is_idle:
                            target = self.findTarget(m,shootFlying = True)
                            if not target:
                                target = self.main_base_ramp.top_center
                            else:
                                target = target.position
                            await self.do(m.attack(target))
                    for m in marauders:
                        if m.is_idle:
                            target = self.findTarget(m,shootFlying = False)
                            if not target:
                                target = self.main_base_ramp.top_center
                            else:
                                target = target.position
                            await self.do(m.attack(target))
                    
                
            elif len(marauders)+len(marines) >5:
                visibles = self.findVisibleEnemies()
                if len(visibles)>0:
                    self.recalled = False
                    for m in marines:
                        if m.is_idle:
                            target = self.findTarget(m,shootFlying = True)
                            if not target:
                                target = self.main_base_ramp.top_center
                            else:
                                target = target.position
                            await self.do(m.attack(target))
                    for m in marauders:
                        if m.is_idle:
                            target = self.findTarget(m,shootFlying = False)
                            if not target:
                                target = self.main_base_ramp.top_center
                            else:
                                target = target.position
                            await self.do(m.attack(target))
                
                else:
                    self.attacking = False
                    if not self.recalled:
                        for m in marines + marauders:
                            await self.do(m.move(self.rallyPoint))
                            self.movingUnits.append((m.tag,self.rallyPoint))
                        self.recalled = True
                        
        
    async def build_workers(self):
        for cc in self.units(COMMANDCENTER).ready.noqueue:
            workers = len(self.units(SCV).closer_than(15,cc.position))
            minerals = len(self.state.mineral_field.closer_than(15,cc.position))
            if minerals > 4:
                if workers < 18:
                    if self.can_afford(SCV):
                        await self.do(cc.train(SCV))
    
    async def manage_supply(self):
        if self.supply_cap <200:
            ccs = self.units(COMMANDCENTER).ready
            
            if self.supply_left == 0 and self.already_pending(SUPPLYDEPOT) < 2:
                if ccs.exists:
                    if self.can_afford(SUPPLYDEPOT):
                        await self.build(SUPPLYDEPOT, near = random.choice(ccs))
                        print("Building extra depots to meet demand")
            
            elif self.supply_left < 5 and not self.already_pending(SUPPLYDEPOT):
                if ccs.exists:
                    if self.can_afford(SUPPLYDEPOT):
                        await self.build(SUPPLYDEPOT, near = random.choice(ccs))
        
    async def manage_expansion(self):
        if len(self.units(COMMANDCENTER)) < self.elapsedTime/180:
            if self.can_afford(COMMANDCENTER):
                if not self.already_pending(COMMANDCENTER):
                    await self.expand_now()
                self.trainUnits = True
            else:
                self.trainUnits = False
        else:
            if not self.trainUnits:
                self.trainUnits = True

    async def manage_refineries(self):
        ccs = self.units(COMMANDCENTER).ready
        for cc in ccs:
            gas = self.state.vespene_geyser.closer_than(15,cc.position)
            for node in gas:
                if self.can_afford(REFINERY):
                    worker = self.select_build_worker(node.position)
                    if worker is not None:
                        if not self.units(REFINERY).closer_than(1,node).exists:
                            await self.do(worker.build(REFINERY,node))
                else:
                    break

    async def modified_find_placement(self, building, near, max_distance=20, random_alternative=True, placement_step=2):
        """Finds a placement location for building."""

        assert isinstance(building, (AbilityId, UnitTypeId))
        #assert self.can_afford(building) using this for buildings already built
        assert isinstance(near, Point2)

        if isinstance(building, UnitTypeId):
            building = self._game_data.units[building.value].creation_ability
        else: # AbilityId
            building = self._game_data.abilities[building.value]

        if await self.can_place(building, near):
            return near

        if max_distance == 0:
            return None

        for distance in range(placement_step, max_distance, placement_step):
            possible_positions = [Point2(p).offset(near).to2 for p in (
                [(dx, -distance) for dx in range(-distance, distance+1, placement_step)] +
                [(dx,  distance) for dx in range(-distance, distance+1, placement_step)] +
                [(-distance, dy) for dy in range(-distance, distance+1, placement_step)] +
                [( distance, dy) for dy in range(-distance, distance+1, placement_step)]
            )]
            res = await self._client.query_building_placement(building, possible_positions)
            possible = [p for r, p in zip(res, possible_positions) if r == ActionResult.Success]
            if not possible:
                continue

            if random_alternative:
                return random.choice(possible)
            else:
                return min(possible, key=lambda p: p.distance_to(near))
        return None

def determineWinner(_result):
    try:
        if _result[0] != None:
            if _result[0] == _result[0].Victory:
                return True
            elif _result[0] == _result[0].Defeat:
                return False
        
        if _result[1] != None:
            if _result[1] == _result[1].Victory:
                return True
            elif _result[1] == _result[0].Defeat:
                return False
            
    except:
        if _result == _result.Victory:
            return True
        elif _result == _result.Defeat:
            return True

def completeBestOfSeries(_map,player1,player2,numberOfGames,_realtime = False): #playerbot MUST be player 1 if playing default AI due to API restrains
    results = {"player1":0,"player2":0}
    
    while max(results.values()) < math.floor(numberOfGames/2)+1:
        x = run_game(maps.get(_map),[player1,player2],realtime = _realtime)
        if determineWinner(x):
            results["player1"]+=1
        else:
            results["player2"]+=1
        time.sleep(1)
            
    print("The best of {} series ends with {} games for player1 and {} games for player2.".format(str(numberOfGames),
          str(results["player1"]),str(results["player2"])))
    if results["player1"] > results['player2']:
        print("player1 wins!")
    else:
        print("player2 wins!")
        
        


if __name__ == "__main__":
    #completeBestOfSeries("AbyssalReefLE",Bot(Race.Terran, rockBot()),Bot(Race.Protoss, SentdeBot()),7,_realtime = False)
    completeBestOfSeries("AbyssalReefLE",Bot(Race.Terran, rockBot()),Computer(Race.Zerg, Difficulty.Hard),3,_realtime = False)
    #Bot(Race.Protoss, SentdeBot())
    
