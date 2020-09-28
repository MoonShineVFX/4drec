#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "Engine/Texture2D.h"
#include "IImageWrapperModule.h"
#include "ImageDecoder.generated.h"


USTRUCT()
struct FOURDREC_API FImageDecodeResult
{
	GENERATED_BODY()

	UPROPERTY()
		UTexture2D* Texture;
	UPROPERTY()
		int32 Index;

	FImageDecodeResult();
	FImageDecodeResult(UTexture2D* InTexture, int32 InIndex);
};


UCLASS()
class FOURDREC_API UImageDecoder : public UObject
{
	GENERATED_BODY()
	
public:
	static UImageDecoder* Create(UObject* Outer, const TArray<uint8>* ImageBuffer, int32 Index, IImageWrapperModule* ImageWrapperModule);

	static FImageDecodeResult DecodeBuffer(UObject* Outer, const TArray<uint8>* ImageBuffer, int32 Index, IImageWrapperModule* ImageWrapperModule);

	DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnImageDecodeCompleted, FImageDecodeResult, DecodeResult);

	FOnImageDecodeCompleted& OnDecodeCompleted()
	{
		return DecodeCompleted;
	}

private:
	void StartDecodeAsync(UObject* Outer, const TArray<uint8>* ImageBuffer, int32 Index, IImageWrapperModule* ImageWrapperModule);
	FOnImageDecodeCompleted DecodeCompleted;
	TFuture<FImageDecodeResult> Future;
};
