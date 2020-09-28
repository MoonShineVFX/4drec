#include "FourdRecDataFactory.h"
#include "FourdRecData.h"
#include "PlatformFilemanager.h"
#include "AssetRegistryModule.h"
#include <EngineGlobals.h>
#include "Misc/Paths.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include <Runtime/Engine/Classes/Engine/Engine.h>


UFourdRecDataFactory::UFourdRecDataFactory()
{
	Formats.Add("4dr;4DREC Record Data");
	bCreateNew = false;
	bEditorImport = true;
	SupportedClass = UFourdRecData::StaticClass();
	FEditorDelegates::OnAssetsPreDelete.AddUObject(this, &UFourdRecDataFactory::OnAssetPreDeleted);
	FEditorDelegates::OnAssetsDeleted.AddUObject(this, &UFourdRecDataFactory::OnAssetDeleted);
}

UObject* UFourdRecDataFactory::FactoryCreateFile(UClass* InClass, UObject* InParent, FName InName, EObjectFlags Flags, const FString& Filename, const TCHAR* Parms, FFeedbackContext* Warn, bool& bOutOperationCanceled)
{
	uint8* FileBuffer;
	const uint64 FileSize = LoadFileToBuffer(Filename, FileBuffer);

	if (FileSize == 0) return nullptr;

	UFourdRecData* FourdRecData = NewObject<UFourdRecData>(InParent, InClass, InName, Flags);

	FString PackageName = FString::Printf(TEXT("/Game/%s/"), *FPaths::GetBaseFilename(Filename));

	UFourdRecTexture* FourdTexture = CreateTextureAsset(PackageName, "Texture");
	FourdRecData->TexturePtr = TSoftObjectPtr<UFourdRecTexture>(FourdTexture);

	uint64 FileBufferCursor = 0;

	FMemory::Memcpy(&FourdRecData->FrameCount, FileBuffer, sizeof(int32));
	FileBufferCursor += sizeof(int32);

	FMemory::Memcpy(&FourdRecData->FPS, FileBuffer + sizeof(uint32), sizeof(float));
	FileBufferCursor += sizeof(float);

	// Create Assets
	for (int32 i = 0; i < FourdRecData->FrameCount; i++)
	{
		uint32 VertexCount;
		TArray<FVector> Vertices;
		TArray<uint32> Triangles;
		TArray<FVector2D> Uvs;

		FMemory::Memcpy(&VertexCount, FileBuffer + FileBufferCursor, sizeof(uint32));
		FileBufferCursor += sizeof(uint32);

		uint32 DecompressedSize;
		FMemory::Memcpy(&DecompressedSize, FileBuffer + FileBufferCursor, sizeof(uint32));
		FileBufferCursor += sizeof(uint32);

		uint32 CompressedSize;
		FMemory::Memcpy(&CompressedSize, FileBuffer + FileBufferCursor, sizeof(uint32));
		FileBufferCursor += sizeof(uint32);

		// decompress geometry data
		uint8* DecompressedBuffer = static_cast<uint8*>(FMemory::Malloc(DecompressedSize));
		FCompression::UncompressMemory(
			NAME_Zlib, static_cast<void*>(DecompressedBuffer), DecompressedSize, FileBuffer + FileBufferCursor, CompressedSize);
		FileBufferCursor += CompressedSize;
		uint32 DecompressedBufferCursor = 0;

		Vertices.AddUninitialized(VertexCount);
		FMemory::Memcpy(Vertices.GetData(), DecompressedBuffer + DecompressedBufferCursor, VertexCount * 3 * sizeof(float));
		DecompressedBufferCursor += VertexCount * 3 * sizeof(float);

		Triangles.AddUninitialized(VertexCount);
		FMemory::Memcpy(Triangles.GetData(), DecompressedBuffer + DecompressedBufferCursor, VertexCount * sizeof(int32));
		DecompressedBufferCursor += VertexCount * sizeof(int32);

		Uvs.AddUninitialized(VertexCount);
		FMemory::Memcpy(Uvs.GetData(), DecompressedBuffer + DecompressedBufferCursor, VertexCount * 2 * sizeof(float));
		DecompressedBufferCursor += VertexCount * 2 * sizeof(float);

		FMemory::Free(DecompressedBuffer);

		// texture data
		uint32 ImageBufferSize;
		FMemory::Memcpy(&ImageBufferSize, FileBuffer + FileBufferCursor, sizeof(uint32));
		FileBufferCursor += sizeof(uint32);

		TArray<uint8> ImageBuffer;
		ImageBuffer.AddUninitialized(ImageBufferSize);
		FMemory::Memcpy(ImageBuffer.GetData(), FileBuffer + FileBufferCursor, ImageBufferSize);
		FileBufferCursor += ImageBufferSize;

		// Asset
		UStaticMesh* Mesh = CreateMeshAsset(PackageName, FString::Printf(TEXT("Mesh_%04d"), i), VertexCount, Vertices, Triangles, Uvs);
		FourdRecData->MeshPtrs.Add(TSoftObjectPtr<UStaticMesh>(Mesh));

		FourdTexture->ImageBuffers.Add(FImageBufferContainer(ImageBuffer));
	}

	FourdRecData->PackageName = PackageName;

	return FourdRecData;
}

void UFourdRecDataFactory::OnAssetPreDeleted(const TArray<UObject*>& DeletedAssetObjects)
{
	PackageNames.Empty();
	for (auto DeletedAssetObject : DeletedAssetObjects)
	{
		if (DeletedAssetObject->GetClass()->IsChildOf(UFourdRecData::StaticClass()))
		{
			UFourdRecData* Data = Cast<UFourdRecData>(DeletedAssetObject);
			PackageNames.Add(Data->PackageName);
		}
	}
}

void UFourdRecDataFactory::OnAssetDeleted(const TArray<UClass*>& DeletedAssetClasses)
{
	bool HasFourd = false;
	for (auto DeletedAssetClass : DeletedAssetClasses)
	{
		if (DeletedAssetClass->IsChildOf(UFourdRecData::StaticClass()))
		{
			HasFourd = true;
			break;
		}
	}
	if (HasFourd)
	{
		for (FString PackageName : PackageNames)
		{
			bool operation = UEditorAssetLibrary::DeleteDirectory(PackageName);
		}
	}
}

uint32 UFourdRecDataFactory::LoadFileToBuffer(const FString& Filename, uint8*& FileBuffer)
{
	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	IFileHandle* FileHandle = PlatformFile.OpenRead(*Filename);
	if (FileHandle)
	{
		const uint64 FileSize = PlatformFile.FileSize(*Filename);
		FileBuffer = static_cast<uint8*>(FMemory::Malloc(FileSize));
		UE_LOG(LogTemp, Warning, TEXT("File %s found with size %d!"), *Filename, FileSize);
		FileHandle->Read(FileBuffer, FileSize);
		delete FileHandle;
		return FileSize;
	}
	UE_LOG(LogTemp, Warning, TEXT("File %s not found!"), *Filename);
	return 0;
}

UStaticMesh* UFourdRecDataFactory::CreateMeshAsset(
	const FString& PackageName, const FString& AssetName, const uint32 VertexCount,
	const TArray<FVector>& Vertices, const TArray<uint32>& Triangles, const TArray<FVector2D>& Uvs)
{
	UPackage* Package = CreatePackage(NULL, *(PackageName + AssetName));
	Package->FullyLoad();

	UStaticMesh* FourdStaticMesh = NewObject<UStaticMesh>(Package, FName(*AssetName), RF_Public | RF_Standalone);

	FRawMesh RawMesh = FRawMesh();
	RawMesh.VertexPositions = Vertices;
	RawMesh.WedgeIndices = Triangles;
	RawMesh.WedgeTexCoords[0] = Uvs;
	RawMesh.WedgeColors.Init(FColor(255, 255, 255), VertexCount);
	RawMesh.WedgeTangentX.Init(FVector(0, 0, 0), VertexCount);
	RawMesh.WedgeTangentY.Init(FVector(0, 0, 0), VertexCount);
	RawMesh.WedgeTangentZ.Init(FVector(0, 0, 0), VertexCount);
	RawMesh.FaceMaterialIndices.Init(0, VertexCount / 3);
	RawMesh.FaceSmoothingMasks.Init(0xFFFFFFFF, VertexCount / 3);

	FourdStaticMesh->SetNumSourceModels(1);
	FStaticMeshSourceModel& SourceModel = FourdStaticMesh->GetSourceModel(0);
	SourceModel.RawMeshBulkData->SaveRawMesh(RawMesh);

	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, TEXT("Material'/fourdrec/FourdRecMaterial.FourdRecMaterial'"));
	FourdStaticMesh->StaticMaterials.Add(FStaticMaterial(Material));

	SourceModel.BuildSettings.bRecomputeNormals = false;
	SourceModel.BuildSettings.bRecomputeTangents = false;
	SourceModel.BuildSettings.bUseMikkTSpace = false;
	SourceModel.BuildSettings.bGenerateLightmapUVs = false;
	SourceModel.BuildSettings.bBuildAdjacencyBuffer = false;
	SourceModel.BuildSettings.bBuildReversedIndexBuffer = false;
	SourceModel.BuildSettings.bUseFullPrecisionUVs = false;
	SourceModel.BuildSettings.bUseHighPrecisionTangentBasis = false;
	SourceModel.BuildSettings.bRemoveDegenerates = false;

	FourdStaticMesh->ImportVersion = EImportStaticMeshVersion::LastVersion;
	FourdStaticMesh->Build(false);

	Package->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(FourdStaticMesh);

	FString PackageFileName = FPackageName::LongPackageNameToFilename(PackageName + AssetName, FPackageName::GetAssetPackageExtension());
	UPackage::SavePackage(Package, FourdStaticMesh, RF_Public | RF_Standalone, *PackageFileName, GError, nullptr, true, true, SAVE_NoError);

	return FourdStaticMesh;
}

UFourdRecTexture* UFourdRecDataFactory::CreateTextureAsset(const FString& PackageName, const FString& AssetName)
{
	UPackage* Package = CreatePackage(NULL, *(PackageName + AssetName));
	Package->FullyLoad();

	UFourdRecTexture* FourdTexture = NewObject<UFourdRecTexture>(Package, FName(*AssetName), RF_Public | RF_Standalone);

	Package->MarkPackageDirty();
	FAssetRegistryModule::AssetCreated(FourdTexture);

	return FourdTexture;
}