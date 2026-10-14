#ifndef PLAYERBOTASSISTTASK_H_
#define PLAYERBOTASSISTTASK_H_

#include "engine/engine.h"
#include "PlayerbotManager.h"

namespace server {
namespace zone {
namespace managers {
namespace playerbots {

class PlayerbotAssistTask : public Task {
public:
	void run() {
		PlayerbotManager::instance()->updateAllAssists();
		schedule(500);
	}
};

} // namespace playerbots
} // namespace managers
} // namespace zone
} // namespace server

#endif // PLAYERBOTASSISTTASK_H_