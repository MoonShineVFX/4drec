from define import ResolveStep

from .feature import (
    ConvertSFM, FeatureExtraction, FeatureMatching, StructureFromMotion,
    MaskImages, PrepareDenseSceneWithMask, PrepareDenseScene, ClipLandmarks
)
from .calibrate import (
    ConstructFromAruco, GenerateSFM, TransformStructure, AlignStructure
)
from .depth import DepthMapEstimation
from .mesh import (
    DepthMapFiltering, Meshing, MeshFiltering, MeshClipping,
    MeshDecimate, Texturing, Package, OptimizeStorage
)


flow_pipeline = {
    ResolveStep.CALIBRATE: [
        ConstructFromAruco, GenerateSFM,
        TransformStructure, AlignStructure
    ],
    ResolveStep.FEATURE: [
        ConvertSFM, FeatureExtraction, FeatureMatching,
        StructureFromMotion, ClipLandmarks, MaskImages,
        PrepareDenseSceneWithMask, PrepareDenseScene
    ],
    ResolveStep.DEPTH: [DepthMapEstimation],
    ResolveStep.MESH: [
        DepthMapFiltering, Meshing,  MeshFiltering,
        MeshClipping, MeshDecimate,
        Texturing, Package, OptimizeStorage
    ]
}

flow_dict = {}

for step in flow_pipeline.values():
    for flow in step:
        flow_dict[flow.__name__] = flow
