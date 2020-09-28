#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "FourdRecTexture.generated.h"


USTRUCT()
struct FOURDREC_API FImageBufferContainer
{
	GENERATED_BODY()

		UPROPERTY()
		TArray<uint8> Buffer;

	FImageBufferContainer();
	FImageBufferContainer(TArray<uint8> InBuffer);
};


UCLASS()
class FOURDREC_API UFourdRecTexture : public UObject
{
	GENERATED_BODY()

public:
	UPROPERTY()
		TArray<FImageBufferContainer> ImageBuffers;
};
