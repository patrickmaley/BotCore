#include "PlayerbotSession.h"

using namespace server::zone::managers::playerbots;

PlayerbotSession::PlayerbotSession() : ZoneClientSession((DummyConstructorParameter*)nullptr) {
}

PlayerbotSession::~PlayerbotSession() {
}

void PlayerbotSession::disconnect(bool lockPlayer) {
    // no-op for bots
}

void PlayerbotSession::sendMessage(BaseMessage* msg) {
    if (msg != nullptr)
        delete msg;
}

void PlayerbotSession::sendMessage(StandaloneBaseMessage* msg) {
    if (msg != nullptr)
        delete msg;
}