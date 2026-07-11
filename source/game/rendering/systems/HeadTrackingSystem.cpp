//
//  HeadTrackingSystem.cpp
//  ProjectRetro
//

#include "HeadTrackingSystem.h"
#include "../components/HeadTrackingSingletonComponent.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstdio>

////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

const int HeadTrackingSystem::HEAD_TRACKING_UDP_PORT = 45123;

////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

HeadTrackingSystem::HeadTrackingSystem(ecs::World& world)
    : BaseSystem(world)
{
    auto headTrackingComponent = std::make_unique<HeadTrackingSingletonComponent>();

    // Non-blocking UDP socket bound to localhost; the Python sidecar sends
    // "hx hy hz" datagrams here at ~30-60 Hz. If binding fails (e.g. port in
    // use) the effect just stays neutral -- the game runs fine regardless.
    const int socketFd = socket(AF_INET, SOCK_DGRAM, 0);
    if (socketFd >= 0)
    {
        sockaddr_in address {};
        address.sin_family      = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port        = htons(static_cast<uint16_t>(HEAD_TRACKING_UDP_PORT));

        if (bind(socketFd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0)
        {
            fcntl(socketFd, F_SETFL, O_NONBLOCK);
            headTrackingComponent->mSocketFd = socketFd;
        }
        else
        {
            close(socketFd);
        }
    }

    mWorld.SetSingletonComponent<HeadTrackingSingletonComponent>(std::move(headTrackingComponent));
}

////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////

void HeadTrackingSystem::VUpdateAssociatedComponents(const float) const
{
    auto& headTrackingComponent = mWorld.GetSingletonComponent<HeadTrackingSingletonComponent>();
    if (headTrackingComponent.mSocketFd < 0)
    {
        return;
    }

    // Drain the socket to the most recent datagram (we only care about latest).
    char buffer[128];
    float latestX = 0.0f, latestY = 0.0f, latestZ = 0.0f;
    bool  receivedPacket = false;

    ssize_t bytesRead = 0;
    while ((bytesRead = recv(headTrackingComponent.mSocketFd, buffer, sizeof(buffer) - 1, 0)) > 0)
    {
        buffer[bytesRead] = '\0';
        float x = 0.0f, y = 0.0f, z = 0.0f;
        if (std::sscanf(buffer, "%f %f %f", &x, &y, &z) == 3)
        {
            latestX        = x;
            latestY        = y;
            latestZ        = z;
            receivedPacket = true;
        }
    }

    if (receivedPacket)
    {
        // Extra smoothing on top of the sidecar's own EMA for a steady image.
        const float smoothing = 0.5f;
        headTrackingComponent.mHeadX += smoothing * (latestX - headTrackingComponent.mHeadX);
        headTrackingComponent.mHeadY += smoothing * (latestY - headTrackingComponent.mHeadY);
        headTrackingComponent.mHeadZ += smoothing * (latestZ - headTrackingComponent.mHeadZ);
    }
}
