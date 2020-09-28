#pragma once

#include "CoreMinimal.h"
#include "Factories/Factory.h"
#include "RawMesh.h"
#include "Engine/StaticMesh.h"
#include "FourdRecTexture.h"
#include "FourdRecDataFactory.generated.h"


UCLASS()
class FOURDRECIMPORTER_API UFourdRecDataFactory : public UFactory
{
	GENERATED_BODY()
	
public:
	UFourdRecDataFactory();

	virtual UObject* FactoryCreateFile(UClass* InClass, UObject* InParent, FName InName, EObjectFlags Flags, const FString& Filename, const TCHAR* Parms, FFeedbackContext* Warn, bool& bOutOperationCanceled) override;

private:
	uint32 LoadFileToBuffer(const FString& Filename, uint8*& FileBuffer);
	UStaticMesh* CreateMeshAsset(
		const FString& PackageName, const FString& AssetName, const uint32 VertexCount,
		const TArray<FVector>& Vertices, const TArray<uint32>& Triangles, const TArray<FVector2D>& Uvs);
	UFourdRecTexture* CreateTextureAsset(const FString& PackageName, const FString& AssetName);

	UPROPERTY(Transient)
		TArray<FString> PackageNames;

	void OnAssetPreDeleted(const TArray<UObject*>& DeletedAssetObjects);
	void OnAssetDeleted(const TArray<UClass*>& DeletedAssetClasses);
};
