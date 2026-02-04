import { Suspense, useEffect, useMemo } from "react"
import { Canvas, useLoader } from "@react-three/fiber"
import { Bounds, OrbitControls } from "@react-three/drei"
import { Mesh, MeshStandardMaterial } from "three"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader"
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader"

type Props = {
  url: string
  className?: string
}

function LoadedObj({ url }: { url: string }) {
  const obj = useLoader(OBJLoader, url)
  const material = useMemo(() => new MeshStandardMaterial({ color: "#e2e8f0", roughness: 0.8, metalness: 0.0 }), [])

  useEffect(() => {
    obj.traverse((child) => {
      if (child instanceof Mesh) {
        child.material = material
      }
    })
  }, [material, obj])

  return <primitive object={obj} />
}

function LoadedGltf({ url }: { url: string }) {
  const gltf = useLoader(GLTFLoader, url)
  const material = useMemo(() => new MeshStandardMaterial({ color: "#e2e8f0", roughness: 0.8, metalness: 0.0 }), [])

  useEffect(() => {
    gltf.scene.traverse((child) => {
      if (child instanceof Mesh) {
        child.material = material
      }
    })
  }, [gltf.scene, material])

  return <primitive object={gltf.scene} />
}

function ModelContent({ url }: { url: string }) {
  const lower = url.toLowerCase()
  if (lower.endsWith(".glb") || lower.endsWith(".gltf")) return <LoadedGltf url={url} />
  return <LoadedObj url={url} />
}

export function ModelViewer({ url, className }: Props) {
  return (
    <div className={className}>
      <Canvas camera={{ position: [4, 4, 3], fov: 45 }}>
        <ambientLight intensity={0.65} />
        <directionalLight position={[5, 8, 6]} intensity={0.9} />
        <Suspense fallback={null}>
          <Bounds fit clip margin={1.2}>
            <ModelContent url={url} />
          </Bounds>
        </Suspense>
        <OrbitControls makeDefault />
      </Canvas>
    </div>
  )
}

