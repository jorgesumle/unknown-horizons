# ###################################################
# Copyright (C) 2012 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################

from horizons.world.building.building import BasicBuilding
from horizons.world.building.buildable import BuildableRect, BuildableSingleEverywhere
from horizons.world.building.collectingbuilding import CollectingBuilding
from horizons.world.building.buildingresourcehandler import ProducerBuilding
from horizons.entities import Entities
from horizons.scheduler import Scheduler
from horizons.constants import LAYERS, BUILDINGS
from horizons.gui.tabs import ResourceDepositOverviewTab
from horizons.world.building.building import SelectableBuilding
from horizons.world.component.storagecomponent import StorageComponent
from horizons.world.production.producer import Producer

class NatureBuilding(BuildableRect, BasicBuilding):
	"""Class for objects that are part of the environment, the nature"""
	walkable = True
	layer = LAYERS.OBJECTS

	def __init__(self, **kwargs):
		super(NatureBuilding, self).__init__(**kwargs)

class ProducerNatureBuilding(ProducerBuilding, NatureBuilding):
	pass

class Field(ProducerNatureBuilding):
	walkable = False
	layer = LAYERS.FIELDS

	def initialize(self, **kwargs):
		super(Field, self).initialize( ** kwargs)

		if self.owner == self.session.world.player:
			# make sure to have a farm nearby when we can reasonably assume that the crops are fully grown
			prod_comp = self.get_component(Producer)
			productions = prod_comp.get_productions()
			if not productions:
				print 'Warning: Field is assumed to always produce, but doesn\'t. ', self
			else:
				run_in = Scheduler().get_ticks(productions[0].get_production_time())
				Scheduler().add_new_object(self._check_covered_by_farm, self, run_in=run_in)

	def _check_covered_by_farm(self):
		"""Warn in case there is no farm nearby to cultivate the field"""
		farm_in_range = any( (farm.position.distance( self.position ) <= farm.radius) for farm in
		                     self.settlement.get_buildings_by_id( BUILDINGS.FARM_CLASS ) )
		if not farm_in_range:
			pos = self.position.origin
			self.session.ingame_gui.message_widget.add(pos.x, pos.y, "FIELD_NEEDS_FARM",
			                                           check_duplicate=True)

class AnimalField(CollectingBuilding, Field):
	walkable = False
	def create_collector(self):
		self.animals = []
		for (animal, number) in self.session.db("SELECT unit_id, count FROM animals \
		                                    WHERE building_id = ?", self.id):
			for i in xrange(0, number):
				unit = Entities.units[animal](self, session=self.session)
				unit.initialize()
		super(AnimalField, self).create_collector()

	def remove(self):
		while len(self.animals) > 0:
			self.animals[0].cancel(continue_action=lambda : 42) # don't continue
			self.animals[0].remove()
		super(AnimalField, self).remove()

	def save(self, db):
		super(AnimalField, self).save(db)
		for animal in self.animals:
			animal.save(db)

	def load(self, db, worldid):
		super(AnimalField, self).load(db, worldid)
		self.animals = []
		# units are loaded separatly

class Tree(ProducerNatureBuilding):
	buildable_upon = True
	layer = LAYERS.OBJECTS

	def initialize(self, start_finished=False, **kwargs):
		super(Tree, self).initialize( **kwargs )
		if start_finished:
			self.get_component(Producer).finish_production_now()

class ResourceDeposit(SelectableBuilding, NatureBuilding):
	"""Class for stuff like clay deposits."""
	tearable = False
	layer = LAYERS.OBJECTS
	tabs = (ResourceDepositOverviewTab,)
	enemy_tabs = (ResourceDepositOverviewTab,)
	walkable = False

	def __init__(self, inventory=None, *args, **kwargs):
		super(ResourceDeposit, self).__init__(*args, **kwargs)
		if inventory is not None:
			self.reinit_inventory(inventory)

	def reinit_inventory(self, inventory):
		for res, amount in inventory.iteritems():
			self.get_component(StorageComponent).inventory.alter(res, amount)


	def initialize(self):
		super(ResourceDeposit, self).initialize()
		for resource, min_amount, max_amount in \
		    self.session.db("SELECT resource, min_amount, max_amount FROM deposit_resources WHERE id = ?", \
		                    self.id):
			self.get_component(StorageComponent).inventory.alter(resource, self.session.random.randint(min_amount, max_amount))

class Fish(BuildableSingleEverywhere, ProducerBuilding, BasicBuilding):

	def __init__(self, *args, **kwargs):
		super(Fish,  self).__init__(*args, **kwargs)

		# Make the fish run at different speeds
		multiplier =  0.7 + self.session.random.random() * 0.6
		self._instance.setTimeMultiplier(multiplier)



