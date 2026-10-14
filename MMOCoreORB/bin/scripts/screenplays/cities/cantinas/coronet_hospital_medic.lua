CoronetedHospitalMedicScreenPlay = ScreenPlay:new {
	numberOfActs = 1,
	screenplayName = "CoronetedHospitalMedicScreenPlay",

	planet = "corellia",
	hospitalCell = 1855531,

	spawn = { template = "medic", x = 18.5, z = 0.26, y = -1.2, heading = 180, name = "Venn Thal" }
}

registerScreenPlay("CoronetedHospitalMedicScreenPlay", true)

function CoronetedHospitalMedicScreenPlay:start()
	if (isZoneEnabled(self.planet)) then
		self:spawnMedic()
	end
end

function CoronetedHospitalMedicScreenPlay:spawnMedic()
	local spawn = self.spawn
	local pNpc = spawnMobile(self.planet, spawn.template, 0, spawn.x, spawn.z, spawn.y, spawn.heading, self.hospitalCell)

	if (pNpc == nil) then
		return
	end

	SceneObject(pNpc):setCustomObjectName(spawn.name)
	CreatureObject(pNpc):setPvpStatusBitmask(0)
	CreatureObject(pNpc):setOptionBit(0x100) -- INVULNERABLE

	CreatureObject(pNpc):addSkillMod("private_hospital_healer", 1)
	CreatureObject(pNpc):addSkillMod("healing_ability", 125)
	CreatureObject(pNpc):addSkillMod("healing_wound_treatment", 125)
	CreatureObject(pNpc):addSkillMod("healing_injury_treatment", 125)
	CreatureObject(pNpc):addSkillMod("healing_wound_speed", 100)
	CreatureObject(pNpc):addSkillMod("healing_injury_speed", 100)

	if (CreatureObject(pNpc):isAiAgent()) then
		AiAgent(pNpc):addObjectFlag(0x8000) -- STATIONARY
		AiAgent(pNpc):addObjectFlag(0x10000) -- NOAIAGGRO
		AiAgent(pNpc):clearPatrolPoints()
		AiAgent(pNpc):setOblivious()
		AiAgent(pNpc):setMovementState(0)
		AiAgent(pNpc):setNextPosition(spawn.x, spawn.z, spawn.y, self.hospitalCell)
	end
end
