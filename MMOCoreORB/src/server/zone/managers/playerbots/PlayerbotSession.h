#ifndef PLAYERBOTSESSION_H_
#define PLAYERBOTSESSION_H_

#include "server/zone/ZoneClientSession.h"

namespace server {
namespace zone {
namespace managers {
namespace playerbots {

class PlayerbotSession : public ZoneClientSession {
public:
    PlayerbotSession();
    virtual ~PlayerbotSession();

    void disconnect(bool lockPlayer = true);
    void sendMessage(BaseMessage* msg);
    void sendMessage(StandaloneBaseMessage* msg);

    bool isPlayerBot() const {
        return true;
    }
};

} // namespace playerbots
} // namespace managers
} // namespace zone
} // namespace server

#endif // PLAYERBOTSESSION_H_