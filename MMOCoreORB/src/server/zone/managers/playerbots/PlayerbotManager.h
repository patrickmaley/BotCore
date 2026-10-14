#ifndef PLAYERBOTMANAGER_H_
#define PLAYERBOTMANAGER_H_

#include "engine/engine.h"
#include "server/zone/objects/creature/CreatureObject.h"

namespace server {
namespace zone {
namespace objects {
namespace creature {
namespace ai {
class AiAgent;
} // namespace ai
} // namespace creature
} // namespace objects
} // namespace zone
} // namespace server

namespace server {
namespace zone {
namespace managers {
namespace playerbots {

class PlayerbotManager : public Singleton<PlayerbotManager>, public Object, public Logger {
	VectorMap<String, ManagedReference<CreatureObject*> > bots;
	VectorMap<String, ManagedReference<CreatureObject*> > masters;
	VectorMap<String, bool> assistEnabled;

	void applyFollowState(server::zone::objects::creature::ai::AiAgent* agent, CreatureObject* master);
	bool addBotToGroup(CreatureObject* master, CreatureObject* bot);
	bool prepareBotAsCompanion(CreatureObject* bot, CreatureObject* master);
	ManagedReference<CreatureObject*> findAssistTarget(CreatureObject* master, CreatureObject* bot);

public:
	PlayerbotManager();
	~PlayerbotManager();

	ManagedReference<CreatureObject*> createBot(const String& name,
		const String& mobileTemplate = "acun_solari");

	bool makeBotStay(const String& name);
	bool makeBotFollow(const String& botName, CreatureObject* master);
	bool setBotAssist(const String& botName, bool enabled);
	bool makeBotJoinGroup(const String& botName, CreatureObject* master);

	ManagedReference<CreatureObject*> getBot(const String& name);

	void updateBotAssist(const String& botName);
	void updateAllAssists();
};

} // namespace playerbots
} // namespace managers
} // namespace zone
} // namespace server

#endif // PLAYERBOTMANAGER_H_
