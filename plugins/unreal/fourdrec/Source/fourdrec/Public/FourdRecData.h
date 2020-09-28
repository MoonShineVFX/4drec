#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "Engine/EngineTypes.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "FourdRecTexture.h"
#include "FourdRecData.generated.h"


UCLASS()
class FOURDREC_API UFourdRecData : public UObject
{
	GENERATED_BODY()

public:
	UFourdRecData();

	void LoadAssets(FStreamableDelegate Delegate);

	void UnloadAssets();
	
	UPROPERTY(VisibleAnyWhere, BlueprintReadOnly)
		FString PackageName;

	UPROPERTY(VisibleAnyWhere, BlueprintReadOnly)
		float FPS;

	UPROPERTY(VisibleAnyWhere, BlueprintReadOnly)
		int32 FrameCount;

	UPROPERTY()
		TArray<TSoftObjectPtr<UStaticMesh>> MeshPtrs;

	UPROPERTY()
		TSoftObjectPtr<UFourdRecTexture> TexturePtr;

	UPROPERTY(Transient)
		TArray<FSoftObjectPath> AssetPathList;
};
