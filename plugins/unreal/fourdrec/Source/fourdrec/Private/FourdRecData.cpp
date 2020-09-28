#include "FourdRecData.h"
#include <EngineGlobals.h>
#include <Runtime/Engine/Classes/Engine/Engine.h>
#define print(text) if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 15, FColor::Yellow, text)


UFourdRecData::UFourdRecData()
{
	PackageName = "";
	FPS = -1;
	FrameCount = 0;
}

void UFourdRecData::LoadAssets(FStreamableDelegate Delegate)
{
	FStreamableManager* AssetLoader = new FStreamableManager();
	for (TSoftObjectPtr<UStaticMesh>& MeshPtr : MeshPtrs)
	{
		AssetPathList.AddUnique(MeshPtr.ToSoftObjectPath());
	}
	AssetPathList.Add(TexturePtr.ToSoftObjectPath());

	AssetLoader->RequestAsyncLoad(AssetPathList, Delegate);
}

void UFourdRecData::UnloadAssets()
{
	if (AssetPathList.Num() == 0)
	{
		return;
	}

	FStreamableManager* AssetLoader = new FStreamableManager();
	for (FSoftObjectPath SoftPath : AssetPathList)
	{
		AssetLoader->Unload(SoftPath);
	}
	AssetPathList.Empty();
}