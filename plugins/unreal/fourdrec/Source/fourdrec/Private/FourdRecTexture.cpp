#include "FourdRecTexture.h"


FImageBufferContainer::FImageBufferContainer()
{}

FImageBufferContainer::FImageBufferContainer(TArray<uint8> InBuffer)
{
	Buffer = InBuffer;
}