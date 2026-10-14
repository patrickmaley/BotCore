#include "PlayerbotManager.h"
#include "PlayerbotAssistTask.h"

#include "server/zone/ZoneServer.h"
#include "server/zone/Zone.h"
#include "server/zone/managers/creature/CreatureManager.h"
#include "server/zone/managers/creature/PetManager.h"
#include "server/zone/managers/group/GroupManager.h"
#include "server/zone/managers/combat/CombatManager.h"
#include "server/zone/objects/creature/ai/AiAgent.h"
#include "server/zone/objects/group/GroupObject.h"
#include "server/zone/objects/intangible/PetControlDevice.h"
#include "templates/params/ObserverEventType.h"
#include "server/ServerCore.h"
#include "templates/params/creature/ObjectFlag.h"

using namespace server::zone::managers::playerbots;

PlayerbotManager::PlayerbotManager() : Logger("PlayerbotManager") {
	setLogging(true);
	setGlobalLogging(true);

	bots.setNoDuplicateInsertPlan();
	bots.setNullValue(nullptr);

	masters.setNoDuplicateInsertPlan();
	masters.setNullValue(nullptr);

	assistEnabled.setNoDuplicateInsertPlan();
	assistEnabled.setNullValue(false);

	PlayerbotAssistTask* task = new PlayerbotAssistTask();
	task->schedule(500);
}

PlayerbotManager::~PlayerbotManager() {
}

ManagedReference<CreatureObject*> PlayerbotManager::getBot(const String& name) {
	return bots.get(name.toLowerCase());
}

void PlayerbotManager::applyFollowState(AiAgent* agent, CreatureObject* master) {
	if (agent == nullptr || master == nullptr)
		return;

	agent->clearPatrolPoints();
	agent->addObjectFlag(ObjectFlag::FOLLOW);
	agent->setFollowObject(master);
	agent->storeFollowObject();
	agent->setMovementState(AiAgent::FOLLOWING);
	agent->setCreatureLink(master, true);

	ManagedReference<PetControlDevice*> pcd = agent->getControlDevice().get().castTo<PetControlDevice*>();
	if (pcd != nullptr) {
		Locker clocker(pcd, agent);
		pcd->setLastCommand(PetManager::FOLLOW);
		pcd->setLastCommander(master);
		pcd->setLastCommandTarget(master);
	}

	float runSpeed = agent->getRunSpeed();
	if (runSpeed > 0.f)
		agent->setWalkSpeed(runSpeed);

	agent->setPosture(CreaturePosture::UPRIGHT, false, false);
}

bool PlayerbotManager::prepareBotAsCompanion(CreatureObject* bot, CreatureObject* master) {
	if (bot == nullptr || master == nullptr || !bot->isAiAgent())
		return false;

	AiAgent* agent = bot->asAiAgent();
	if (agent == nullptr)
		return false;

	bot->setFaction(master->getFaction());
	bot->setCreatureLink(master, true);
	bot->clearOptionBit(OptionBitmask::INVULNERABLE, true);
	bot->setOptionBit(OptionBitmask::AIENABLED, true);

	uint32 pvpMask = master->getPvpStatusBitmask();
	pvpMask &= ~ObjectFlag::PLAYER;
	if (!(pvpMask & ObjectFlag::ATTACKABLE))
		pvpMask |= ObjectFlag::ATTACKABLE;
	bot->setPvpStatusBitmask(pvpMask, true);

	ManagedReference<PetControlDevice*> pcd = bot->getControlDevice().get().castTo<PetControlDevice*>();

	if (pcd == nullptr) {
		ZoneServer* zoneServer = bot->getZoneServer();
		if (zoneServer == nullptr)
			return false;

		ManagedReference<SceneObject*> deviceObj = zoneServer->createObject(String("object/intangible/pet/pet_control.iff").hashCode(), 0);

		if (deviceObj == nullptr || !deviceObj->isPetControlDevice()) {
			error("Failed to create pet control device for bot");
			if (deviceObj != nullptr)
				deviceObj->destroyObjectFromWorld(true);
			return false;
		}

		pcd = deviceObj.castTo<PetControlDevice*>();
		if (pcd == nullptr)
			return false;

		Locker deviceLock(pcd, bot);
		pcd->setControlledObject(bot);
		pcd->setPetType(PetManager::CREATUREPET);
		pcd->setMaxVitality(100);
		pcd->setVitality(100);
		pcd->setGrowthStage(1);
		pcd->setCustomObjectName(bot->getCustomObjectName(), true);
		pcd->setLastCommand(PetManager::FOLLOW);
		pcd->setLastCommander(master);
		bot->setControlDevice(pcd);
	}

	agent->setLairTemplateCRC(0);
	agent->setCreatureBitmask(ObjectFlag::PET);
	agent->addObjectFlag(ObjectFlag::FOLLOW);
	agent->setAITemplate();

	info("Bot prepared as combat companion", true);
	return true;
}

ManagedReference<CreatureObject*> PlayerbotManager::findAssistTarget(CreatureObject* master, CreatureObject* bot) {
	if (master == nullptr || bot == nullptr)
		return nullptr;

	ManagedReference<SceneObject*> defenderObj = master->getMainDefender();

	if (defenderObj == nullptr || !defenderObj->isCreatureObject()) {
		uint64 targetID = master->getTargetID();
		if (targetID == 0)
			return nullptr;

		ZoneServer* zoneServer = ServerCore::getZoneServer();
		if (zoneServer == nullptr)
			return nullptr;

		defenderObj = zoneServer->getObject(targetID);
	}

	if (defenderObj == nullptr || !defenderObj->isCreatureObject())
		return nullptr;

	ManagedReference<CreatureObject*> enemy = defenderObj->asCreatureObject();
	if (enemy == nullptr || enemy.get() == bot || enemy.get() == master)
		return nullptr;

	if (enemy->isDead() || enemy->isIncapacitated())
		return nullptr;

	const bool masterFighting = master->isInCombat() || master->hasDefender(enemy) || enemy->hasDefender(master);
	if (!masterFighting)
		return nullptr;

	if (!enemy->isAttackableBy(bot) && !enemy->isAttackableBy(master))
		return nullptr;

	return enemy;
}

bool PlayerbotManager::addBotToGroup(CreatureObject* master, CreatureObject* bot) {
	if (master == nullptr || bot == nullptr)
		return false;

	ManagedReference<GroupObject*> masterGroup = master->getGroup();
	ManagedReference<GroupObject*> botGroup = bot->getGroup();

	if (masterGroup != nullptr && botGroup == masterGroup)
		return true;

	if (botGroup != nullptr) {
		Locker botLock(bot);
		GroupManager::instance()->leaveGroup(botGroup, bot);
	}

	{
		Locker masterLock(master);
		GroupManager::instance()->inviteToGroup(master, bot);
	}

	GroupManager::instance()->joinGroup(bot);

	return bot->getGroup() != nullptr;
}

ManagedReference<CreatureObject*> PlayerbotManager::createBot(const String& name, const String& mobileTemplate) {
	ZoneServer* zoneServer = ServerCore::getZoneServer();
	if (zoneServer == nullptr) {
		error("ZoneServer is null");
		return nullptr;
	}

	Zone* zone = zoneServer->getZone("corellia");
	if (zone == nullptr) {
		error("Zone corellia not found");
		return nullptr;
	}

	CreatureManager* creatureManager = zone->getCreatureManager();
	if (creatureManager == nullptr) {
		error("CreatureManager is null");
		return nullptr;
	}

	String mobileName = mobileTemplate;
	uint32 mobileCrc = mobileName.hashCode();

	const float x = -147.0f;
	const float z = 28.0f;
	const float y = -4723.0f;

	info("Spawning mobile '" + mobileName + "' as bot '" + name + "'", true);

	ManagedReference<CreatureObject*> bot =
		creatureManager->spawnCreature(mobileCrc, 0, x, z, y, 0, false, 0.f);

	if (bot == nullptr) {
		error("spawnCreature failed for mobile: " + mobileName);
		return nullptr;
	}

	Locker locker(bot);

	bot->setCustomObjectName(name, true);
	bot->setPvpStatusBitmask(ObjectFlag::ATTACKABLE, true);
	bot->clearOptionBit(OptionBitmask::INVULNERABLE, true);
	bot->setOptionBit(OptionBitmask::AIENABLED, true);

	if (bot->isAiAgent()) {
		AiAgent* agent = bot->asAiAgent();
		if (agent != nullptr) {
			agent->setHomeLocation(x, z, y, nullptr, 0.f);
			agent->setNextStepPosition(x, z, y);
			agent->clearPatrolPoints();
			agent->setFollowObject(nullptr);
			agent->setMovementState(AiAgent::OBLIVIOUS);
		}
	}

	bots.put(name.toLowerCase(), bot);
	assistEnabled.put(name.toLowerCase(), false);

	info("Bot spawned and set to stay: " + name, true);
	return bot;
}

bool PlayerbotManager::makeBotStay(const String& name) {
	ManagedReference<CreatureObject*> bot = getBot(name);
	if (bot == nullptr) {
		error("No bot named: " + name);
		return false;
	}

	Locker locker(bot);

	if (!bot->isAiAgent()) {
		error("Bot is not AiAgent: " + name);
		return false;
	}

	AiAgent* agent = bot->asAiAgent();
	if (agent == nullptr)
		return false;

	if (bot->isInCombat())
		CombatManager::instance()->attemptPeace(bot);

	ManagedReference<PetControlDevice*> pcd = bot->getControlDevice().get().castTo<PetControlDevice*>();
	bot->setControlDevice(nullptr);
	if (pcd != nullptr) {
		Locker deviceLock(pcd, bot);
		pcd->setControlledObject(nullptr);
		pcd->destroyObjectFromWorld(true);
	}

	agent->removeObjectFlag(ObjectFlag::FOLLOW);
	agent->removeObjectFlag(ObjectFlag::PET);
	agent->setFollowObject(nullptr);
	agent->storeFollowObject();
	agent->clearPatrolPoints();
	agent->setCreatureLink(nullptr, true);
	agent->setAITemplate();
	agent->setHomeLocation(bot->getPositionX(), bot->getPositionZ(), bot->getPositionY(),
		bot->getParent().get().castTo<CellObject*>(), 0.f);
	agent->setMovementState(AiAgent::OBLIVIOUS);

	ManagedReference<GroupObject*> group = bot->getGroup();
	if (group != nullptr)
		GroupManager::instance()->leaveGroup(group, bot);

	masters.drop(name.toLowerCase());
	assistEnabled.put(name.toLowerCase(), false);

	info("Bot now staying: " + name, true);
	return true;
}

bool PlayerbotManager::makeBotFollow(const String& botName, CreatureObject* master) {
	if (master == nullptr) {
		error("makeBotFollow: master is null");
		return false;
	}

	ManagedReference<CreatureObject*> bot = getBot(botName);
	if (bot == nullptr) {
		error("No bot named: " + botName);
		return false;
	}

	{
		Locker locker(bot);

		if (!bot->isAiAgent()) {
			error("Bot is not AiAgent: " + botName);
			return false;
		}

		AiAgent* agent = bot->asAiAgent();
		if (agent == nullptr)
			return false;

		if (bot->isInCombat())
			CombatManager::instance()->attemptPeace(bot);

		Zone* masterZone = master->getZone();
		if (masterZone != nullptr) {
			Zone* botZone = bot->getZone();
			const float dx = bot->getWorldPositionX() - master->getWorldPositionX();
			const float dy = bot->getWorldPositionY() - master->getWorldPositionY();
			const bool differentZone = botZone == nullptr || botZone != masterZone;
			const bool tooFar = (dx * dx + dy * dy) > (32.f * 32.f);

			if (differentZone || tooFar) {
				bot->switchZone(masterZone->getZoneName(),
					master->getPositionX() + 2.f,
					master->getPositionZ(),
					master->getPositionY() + 2.f,
					master->getParentID());
			}
		}

		if (!prepareBotAsCompanion(bot, master)) {
			error("Failed to prepare bot as companion: " + botName);
			return false;
		}

		applyFollowState(agent, master);

		masters.put(botName.toLowerCase(), master);
		assistEnabled.put(botName.toLowerCase(), true);
	}

	if (!addBotToGroup(master, bot))
		warning("Bot '" + botName + "' is following but failed to join the group");

	info("Bot '" + botName + "' now following '" + master->getFirstName() + "'", true);
	return true;
}

bool PlayerbotManager::makeBotJoinGroup(const String& botName, CreatureObject* master) {
	if (master == nullptr)
		return false;

	ManagedReference<CreatureObject*> bot = getBot(botName);
	if (bot == nullptr) {
		error("No bot named: " + botName);
		return false;
	}

	return addBotToGroup(master, bot);
}

bool PlayerbotManager::setBotAssist(const String& botName, bool enabled) {
	ManagedReference<CreatureObject*> bot = getBot(botName);
	if (bot == nullptr) {
		error("No bot named: " + botName);
		return false;
	}

	assistEnabled.put(botName.toLowerCase(), enabled);
	info("Bot '" + botName + "' assist=" + String::valueOf(enabled), true);

	if (enabled)
		updateBotAssist(botName);

	return true;
}

void PlayerbotManager::updateBotAssist(const String& botName) {
	String key = botName.toLowerCase();

	ManagedReference<CreatureObject*> bot = getBot(key);
	ManagedReference<CreatureObject*> master = masters.get(key);

	if (bot == nullptr || master == nullptr)
		return;

	Locker locker(bot);

	if (!bot->isAiAgent())
		return;

	AiAgent* agent = bot->asAiAgent();
	if (agent == nullptr)
		return;

	if (bot->isDead() || bot->isIncapacitated())
		return;

	if (!assistEnabled.get(key)) {
		if (!bot->isInCombat())
			applyFollowState(agent, master);
		return;
	}

	ManagedReference<CreatureObject*> enemy = findAssistTarget(master, bot);

	if (enemy != nullptr) {
		ManagedReference<SceneObject*> currentFollow = agent->getFollowObject().get();
		if (bot->isInCombat() && currentFollow != nullptr && currentFollow->getObjectID() == enemy->getObjectID())
			return;

		ManagedReference<PetControlDevice*> pcd = bot->getControlDevice().get().castTo<PetControlDevice*>();
		if (pcd != nullptr) {
			Locker clocker(pcd, bot);
			pcd->setLastCommand(PetManager::ATTACK);
			pcd->setLastCommander(master);
			pcd->setLastCommandTarget(enemy);
		}

		info("Bot '" + botName + "' assisting on " + enemy->getDisplayedName(), true);

		agent->setDefender(enemy);
		agent->notifyObservers(ObserverEventType::STARTCOMBAT, master);
		agent->selectDefaultAttack();
		agent->enqueueAttack();
		return;
	}

	if (bot->isInCombat())
		CombatManager::instance()->attemptPeace(bot);

	applyFollowState(agent, master);
}

void PlayerbotManager::updateAllAssists() {
	for (int i = 0; i < masters.size(); ++i) {
		String name = masters.elementAt(i).getKey();
		updateBotAssist(name);
	}
}
