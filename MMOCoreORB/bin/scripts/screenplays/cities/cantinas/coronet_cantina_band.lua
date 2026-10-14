CoronetedCantinaBandScreenPlay = ScreenPlay:new {
	numberOfActs = 1,
	screenplayName = "CoronetedCantinaBandScreenPlay",

	planet = "corellia",
	cantinaCell = 8105496,
	floorZ = -0.895,

	dances = { "theatrical2", "exotic2", "formal2", "lyrical2", "rhythmic2", "popular2", "footloose2", "poplock2", "basic2", "theatrical", "exotic", "formal", "lyrical", "rhythmic", "popular" },
	songs = { "virtuoso", "starwars3", "starwars4", "jazz", "rock", "ceremonial", "waltz", "folk", "ballad", "western", "starwars2", "starwars1" },

	-- Open floor south of the bar counter (bar sits around x=-8, y=-2..3) and east of the west wall.
	spawns = {
		{ template = "entertainer", x = 5.5, z = -0.895, y = -6.8, heading = 90, role = "dancer", name = "Lira Vesh" },
		{ template = "entertainer", x = 7.5, z = -0.895, y = -6.8, heading = 270, role = "dancer", name = "Sera Dune" },
		{ template = "entertainer", x = 6.5, z = -0.895, y = -5.6, heading = 180, role = "dancer", name = "Ryn Kessa" },
		{ template = "bith_musician", x = 5.2, z = -0.895, y = -8.0, heading = 45, role = "musician", name = "Tekk Nal" },
		{ template = "bith_musician", x = 6.5, z = -0.895, y = -8.3, heading = 0, role = "musician", name = "Ool Vinda" },
		{ template = "bith_musician", x = 7.8, z = -0.895, y = -8.0, heading = 315, role = "musician", name = "Plo Nerin" },
	}
}

registerScreenPlay("CoronetedCantinaBandScreenPlay", true)

function CoronetedCantinaBandScreenPlay:start()
	if (isZoneEnabled(self.planet)) then
		self:spawnBand()
	end
end

function CoronetedCantinaBandScreenPlay:spawnBand()
	writeData("coronetBand:count", 0)

	for i = 1, #self.spawns, 1 do
		local spawn = self.spawns[i]
		local pNpc = spawnMobile(self.planet, spawn.template, 0, spawn.x, spawn.z, spawn.y, spawn.heading, self.cantinaCell)

		if (pNpc ~= nil) then
			self:preparePerformer(pNpc, spawn)
			writeData("coronetBand:" .. i, SceneObject(pNpc):getObjectID())
			writeData("coronetBand:count", i)
		end
	end

	local pFirst = getSceneObject(readData("coronetBand:1"))

	if (pFirst ~= nil) then
		createEvent(5000, "CoronetedCantinaBandScreenPlay", "groupBand", pFirst, "")
		createEvent(15000, "CoronetedCantinaBandScreenPlay", "rotatePerformances", pFirst, "")
	end
end

function CoronetedCantinaBandScreenPlay:preparePerformer(pNpc, spawn)
	SceneObject(pNpc):setCustomObjectName(spawn.name)
	CreatureObject(pNpc):setPvpStatusBitmask(0)
	CreatureObject(pNpc):setOptionBit(0x100) -- INVULNERABLE
	CreatureObject(pNpc):addSkillMod("private_buff_mind", 100)
	CreatureObject(pNpc):addSkillMod("healing_dance_mind", 100)
	CreatureObject(pNpc):addSkillMod("healing_music_mind", 100)
	CreatureObject(pNpc):addSkillMod("healing_dance_wound", 125)
	CreatureObject(pNpc):addSkillMod("healing_music_wound", 125)
	CreatureObject(pNpc):addSkillMod("healing_dance_shock", 25)
	CreatureObject(pNpc):addSkillMod("healing_music_shock", 25)
	CreatureObject(pNpc):addSkillMod("private_med_battle_fatigue", 5)

	self:pinPerformer(pNpc, spawn.x, spawn.z, spawn.y)

	createEvent(2000, "CoronetedCantinaBandScreenPlay", "startPerformance", pNpc, spawn.role)
end

function CoronetedCantinaBandScreenPlay:pinPerformer(pNpc, x, z, y)
	if (pNpc == nil or not CreatureObject(pNpc):isAiAgent()) then
		return
	end

	AiAgent(pNpc):addObjectFlag(0x8000) -- STATIONARY
	AiAgent(pNpc):addObjectFlag(0x10000) -- NOAIAGGRO
	AiAgent(pNpc):clearPatrolPoints()
	AiAgent(pNpc):setOblivious()
	AiAgent(pNpc):setMovementState(0) -- OBLIVIOUS
	AiAgent(pNpc):setNextPosition(x, z, y, self.cantinaCell)
end

function CoronetedCantinaBandScreenPlay:startPerformance(pNpc, role)
	if (pNpc == nil or CreatureObject(pNpc):isDead()) then
		return
	end

	self:pinPerformer(pNpc, SceneObject(pNpc):getPositionX(), SceneObject(pNpc):getPositionZ(), SceneObject(pNpc):getPositionY())

	local started = false

	if (role == "dancer") then
		started = CreatureObject(pNpc):startEntertainingDance(self:pickPerformance(self.dances, nil))
	elseif (role == "musician") then
		started = CreatureObject(pNpc):startEntertainingMusic(self:pickPerformance(self.songs, nil))
	end

	if (not started) then
		print("CoronetedCantinaBandScreenPlay: failed to start " .. tostring(role) .. " performance")
		createEvent(10000, "CoronetedCantinaBandScreenPlay", "startPerformance", pNpc, role)
		return
	end

	self:shuffleFlourishes(pNpc)
	createEvent(4000 + getRandomNumber(3000), "CoronetedCantinaBandScreenPlay", "doNextFlourish", pNpc, "")
end

function CoronetedCantinaBandScreenPlay:groupBand()
	local count = readData("coronetBand:count")
	local pLeader = getSceneObject(readData("coronetBand:1"))

	if (pLeader == nil or count < 2) then
		return
	end

	for i = 2, count, 1 do
		local pMember = getSceneObject(readData("coronetBand:" .. i))

		if (pMember ~= nil) then
			CreatureObject(pLeader):formGroupWith(pMember)
		end
	end
end

function CoronetedCantinaBandScreenPlay:rotatePerformances()
	local count = readData("coronetBand:count")
	local danceName = self:pickPerformance(self.dances, nil)
	local songName = self:pickPerformance(self.songs, nil)

	for i = 1, count, 1 do
		local pNpc = getSceneObject(readData("coronetBand:" .. i))

		if (pNpc ~= nil and not CreatureObject(pNpc):isDead()) then
			if (CreatureObject(pNpc):isPlayingMusic()) then
				CreatureObject(pNpc):changeEntertainingPerformance(songName)
			elseif (CreatureObject(pNpc):isDancing()) then
				CreatureObject(pNpc):changeEntertainingPerformance(danceName)
			end
		end
	end

	local pFirst = getSceneObject(readData("coronetBand:1"))

	if (pFirst ~= nil) then
		createEvent(120000 + getRandomNumber(60000), "CoronetedCantinaBandScreenPlay", "rotatePerformances", pFirst, "")
	end
end

function CoronetedCantinaBandScreenPlay:pickPerformance(list, currentName)
	local choice = list[getRandomNumber(#list)]
	local attempts = 0

	while (currentName ~= nil and choice == currentName and attempts < 12) do
		choice = list[getRandomNumber(#list)]
		attempts = attempts + 1
	end

	return choice
end

function CoronetedCantinaBandScreenPlay:shuffleFlourishes(pNpc)
	local order = { 1, 2, 3, 4, 5, 6, 7, 8 }

	for i = 8, 2, -1 do
		local j = getRandomNumber(i)
		order[i], order[j] = order[j], order[i]
	end

	local npcID = SceneObject(pNpc):getObjectID()
	writeData(npcID .. ":flourishIdx", 1)

	for i = 1, 8, 1 do
		writeData(npcID .. ":flourish" .. i, order[i])
	end
end

function CoronetedCantinaBandScreenPlay:doNextFlourish(pNpc)
	if (pNpc == nil or CreatureObject(pNpc):isDead()) then
		return
	end

	if (not CreatureObject(pNpc):isDancing() and not CreatureObject(pNpc):isPlayingMusic()) then
		createEvent(8000, "CoronetedCantinaBandScreenPlay", "doNextFlourish", pNpc, "")
		return
	end

	local npcID = SceneObject(pNpc):getObjectID()
	local idx = readData(npcID .. ":flourishIdx")

	if (idx < 1 or idx > 8) then
		self:shuffleFlourishes(pNpc)
		idx = 1
	end

	CreatureObject(pNpc):doEntertainerFlourish(readData(npcID .. ":flourish" .. idx))

	idx = idx + 1

	if (idx > 8) then
		self:shuffleFlourishes(pNpc)
	else
		writeData(npcID .. ":flourishIdx", idx)
	end

	createEvent(4000 + getRandomNumber(3000), "CoronetedCantinaBandScreenPlay", "doNextFlourish", pNpc, "")
end
