# Game Development Skills — Comprehensive Guide

> **Knowledge Base Reference:** Load these files for deeper domain coverage:
> - `knowledge/game_dev/combat_cinematics_ui.json` — Combat systems (FPS, Souls-like), cinematics, branching dialogue, HUD/UI, technical art
> - `knowledge/game_dev/optimization_platforms_advanced.json` — Performance profiling, draw call optimization, console/VR dev, AAA pipelines, anti-cheat, photogrammetry
> - `knowledge/game_dev/core_programming.json` — C#/C++/GDScript fundamentals, design patterns, ECS, data structures
> - `knowledge/game_dev/rendering_graphics.json` — Render pipelines, shaders (HLSL/GLSL), lighting models, post-processing
> - `knowledge/game_dev/physics_ai.json` — Physics engines, behavior trees, pathfinding, state machines
> - `knowledge/game_dev/game_engines.json` — Unity vs Unreal vs Godot engine-specific deep dives, project architecture
> - `knowledge/game_dev/audio_engineering.json` — FMOD/Wwise integration, spatial audio, adaptive music
> - `knowledge/game_dev/multiplayer_openworld.json` — Netcode, dedicated servers, open-world streaming, replication
> - `knowledge/game_dev/game_design_production.json` — Game design theory, level design, production pipelines, QA

## 1. Unity (C#)

### Project Structure

```
Assets/
├── Animations/           # .anim, .controller
├── Audio/                # .wav, .ogg, .mp3
├── Materials/            # .mat
├── Models/               # .fbx, .obj
├── Prefabs/              # .prefab
├── Resources/            # Loadable at runtime
├── Scenes/               # .unity
├── Scripts/              # .cs
│   ├── Behaviors/
│   ├── Systems/
│   └── UI/
├── Shaders/              # .shader, .hlsl
├── Sprites/              # .png, .jpg
├── Textures/             # .png, .tga
└── UI/                   # .uxml, .uss
```

### GameObject & Component Pattern

```csharp
// Every GameObject is a container for Components

// Bad: monolithic class
public class Player : MonoBehaviour
{
    void Update()
    {
        // Input handling
        // Movement
        // Animation
        // Sound
        // Health
    }
}

// Good: separated concerns
// Player GameObject has:
//   - PlayerInput (handles input)
//   - MovementController (handles physics movement)
//   - HealthController (handles health/damage)
//   - AnimationController (handles animator state)
//   - AudioController (handles sound effects)

[RequireComponent(typeof(CharacterController), typeof(Animator))]
public class MovementController : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float rotationSpeed = 10f;

    private CharacterController characterController;
    private Animator animator;
    private Vector3 moveDirection;

    private void Awake()
    {
        characterController = GetComponent<CharacterController>();
        animator = GetComponent<Animator>();
    }

    public void Move(Vector2 input)
    {
        moveDirection = new Vector3(input.x, 0, input.y).normalized;

        if (moveDirection.magnitude >= 0.1f)
        {
            float targetAngle = Mathf.Atan2(moveDirection.x, moveDirection.z) * Mathf.Rad2Deg;
            transform.rotation = Quaternion.Slerp(
                transform.rotation,
                Quaternion.Euler(0, targetAngle, 0),
                rotationSpeed * Time.deltaTime
            );
        }

        characterController.Move(moveDirection * moveSpeed * Time.deltaTime);
        animator.SetFloat("Speed", characterController.velocity.magnitude);
    }
}

public class PlayerInput : MonoBehaviour
{
    [SerializeField] private MovementController movement;
    [SerializeField] private HealthController health;

    private void Update()
    {
        Vector2 input = new Vector2(Input.GetAxis("Horizontal"), Input.GetAxis("Vertical"));
        movement.Move(input);

        if (Input.GetButtonDown("Jump"))
        {
            // Jump logic
        }

        if (Input.GetMouseButtonDown(0))
        {
            health.TakeDamage(10);
        }
    }
}
```

### Physics

```csharp
// Rigidbody forces
[RequireComponent(typeof(Rigidbody))]
public class PhysicsObject : MonoBehaviour
{
    private Rigidbody rb;

    [SerializeField] private float force = 10f;
    [SerializeField] private float torque = 5f;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
    }

    public void ApplyForce(Vector3 direction)
    {
        rb.AddForce(direction * force, ForceMode.Force);          // Continuous
        rb.AddForce(direction * force, ForceMode.Impulse);        // Instant burst
        rb.AddForce(direction * force, ForceMode.Acceleration);   // Ignore mass
        rb.AddForce(direction * force, ForceMode.VelocityChange); // Instant, ignore mass
    }

    public void ApplyTorque(Vector3 axis)
    {
        rb.AddTorque(axis * torque);
    }

    // Collision events
    private void OnCollisionEnter(Collision collision)
    {
        float impactForce = collision.relativeVelocity.magnitude;
        if (impactForce > 5f)
        {
            PlayImpactSound(impactForce);
        }
    }

    private void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Pickup"))
        {
            CollectItem(other.gameObject);
        }
    }

    // Raycasting
    public bool IsGrounded()
    {
        return Physics.Raycast(
            transform.position,
            Vector3.down,
            1.1f,
            LayerMask.GetMask("Ground")
        );
    }

    // Overlap detection
    public List<Collider> GetNearbyEnemies(float radius)
    {
        Collider[] hits = Physics.OverlapSphere(
            transform.position,
            radius,
            LayerMask.GetMask("Enemy")
        );
        return new List<Collider>(hits);
    }
}
```

### Animation System

```csharp
// Animation parameters
public class AnimationController : MonoBehaviour
{
    [SerializeField] private Animator animator;

    private static readonly int Speed = Animator.StringToHash("Speed");
    private static readonly int Attack = Animator.StringToHash("Attack");
    private static readonly int Hit = Animator.StringToHash("Hit");
    private static readonly int IsDead = Animator.StringToHash("IsDead");
    private static readonly int RandomIdle = Animator.StringToHash("RandomIdle");

    public void SetSpeed(float speed)
    {
        animator.SetFloat(Speed, speed, 0.1f, Time.deltaTime);
    }

    public void PlayAttackAnimation()
    {
        animator.SetTrigger(Attack);
    }

    public void PlayHitAnimation()
    {
        animator.SetTrigger(Hit);
    }

    public void SetDead(bool dead)
    {
        animator.SetBool(IsDead, dead);
    }

    // Animation event callback (called from animation clip)
    public void OnAttackHit()
    {
        // Deal damage at the correct frame
        GetComponent<WeaponController>().DealDamage();
    }

    public void OnFootstep()
    {
        // Play footstep sound
        AudioManager.Instance.PlayFootstep(transform.position);
    }
}
```

### Unity DOTS (Data-Oriented Tech Stack)

```csharp
using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;
using Unity.Burst;

// Component (pure data, no methods)
public struct Velocity : IComponentData
{
    public float3 Value;
}

public struct Health : IComponentData
{
    public float Value;
    public float Max;
}

// Tag component (empty struct for filtering)
public struct EnemyTag : IComponentData { }
public struct PlayerTag : IComponentData { }

// System (logic operating on component data)
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial struct MovementSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        float deltaTime = SystemAPI.Time.DeltaTime;

        new MoveJob
        {
            DeltaTime = deltaTime
        }.ScheduleParallel();
    }
}

[BurstCompile]
public partial struct MoveJob : IJobEntity
{
    public float DeltaTime;

    [BurstCompile]
    private void Execute(ref LocalTransform transform, in Velocity velocity)
    {
        transform.Position += velocity.Value * DeltaTime;
    }
}

// Spawning entities
public class SpawnerSystem : MonoBehaviour
{
    [SerializeField] private GameObject prefab;

    private void Start()
    {
        EntityManager entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;
        Entity prefabEntity = GameObjectConversionUtility.ConvertGameObjectHierarchy(prefab, World.DefaultGameObjectInjectionWorld);

        for (int i = 0; i < 10000; i++)
        {
            Entity entity = entityManager.Instantiate(prefabEntity);
            entityManager.SetComponentData(entity, new Velocity
            {
                Value = new float3(UnityEngine.Random.Range(-1f, 1f), 0, UnityEngine.Random.Range(-1f, 1f))
            });
            entityManager.SetComponentData(entity, LocalTransform.FromPosition(
                UnityEngine.Random.insideUnitSphere * 50
            ));
        }
    }
}
```

### ScriptableObject Pattern

```csharp
// Data-driven design
using UnityEngine;

[CreateAssetMenu(fileName = "NewItem", menuName = "Game/Item")]
public class ItemData : ScriptableObject
{
    public string itemName;
    public string description;
    public Sprite icon;
    public ItemCategory category;
    public float weight;
    public int maxStack = 99;
    public int buyPrice;
    public int sellPrice;
    public GameObject worldPrefab;
    public bool isConsumable;
    public ConsumableEffect effect;
}

public enum ItemCategory
{
    Weapon, Armor, Potion, QuestItem, Material
}

[System.Serializable]
public struct ConsumableEffect
{
    public float healthRestore;
    public float manaRestore;
    public float staminaRestore;
    public float duration;
}

// Usage
public class InventorySlot : MonoBehaviour
{
    [SerializeField] private ItemData item;
    [SerializeField] private int quantity;

    public void Use()
    {
        if (item && quantity > 0)
        {
            PlayerStats stats = GetComponent<PlayerStats>();
            stats.Heal(item.effect.healthRestore);
            stats.RestoreMana(item.effect.manaRestore);
            quantity--;
        }
    }
}
```

### Coroutines & Async

```csharp
using System.Collections;
using UnityEngine;

public class CoroutineExample : MonoBehaviour
{
    // Old style: Coroutines
    public IEnumerator AttackSequence()
    {
        // Wind up
        yield return StartCoroutine(WindUp(0.5f));

        // Swing
        animator.SetTrigger("Swing");
        yield return new WaitForSeconds(0.3f);

        // Deal damage
        DealDamage();

        // Cooldown
        yield return new WaitForSeconds(1f);

        // Ready for next attack
        isAttacking = false;
    }

    public IEnumerator WindUp(float duration)
    {
        float elapsed = 0;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            windUpEffect.alpha = elapsed / duration;
            yield return null;
        }
    }

    // New style: Async/Await
    public async Awaitable MoveOverTime(Vector3 target, float duration)
    {
        Vector3 start = transform.position;
        float elapsed = 0;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float t = elapsed / duration;
            t = t * t * (3f - 2f * t); // Smoothstep
            transform.position = Vector3.Lerp(start, target, t);
            await Awaitable.NextFrameAsync();
        }

        transform.position = target;
    }
}
```

### Object Pooling

```csharp
using System.Collections.Generic;
using UnityEngine;

public class ObjectPool<T> where T : MonoBehaviour
{
    private readonly T prefab;
    private readonly Queue<T> pool = new();
    private readonly Transform parent;

    public ObjectPool(T prefab, int initialSize, Transform parent = null)
    {
        this.prefab = prefab;
        this.parent = parent;

        for (int i = 0; i < initialSize; i++)
        {
            T obj = CreateNew();
            obj.gameObject.SetActive(false);
            pool.Enqueue(obj);
        }
    }

    private T CreateNew()
    {
        T obj = Object.Instantiate(prefab, parent);
        obj.gameObject.name = $"{prefab.name}_{pool.Count}";
        return obj;
    }

    public T Get()
    {
        if (pool.Count == 0)
        {
            return CreateNew();
        }

        T obj = pool.Dequeue();
        obj.gameObject.SetActive(true);
        return obj;
    }

    public void Release(T obj)
    {
        obj.gameObject.SetActive(false);
        obj.transform.SetParent(parent);
        pool.Enqueue(obj);
    }
}

// Usage
public class BulletPool : MonoBehaviour
{
    [SerializeField] private Bullet bulletPrefab;
    [SerializeField] private int poolSize = 50;

    private ObjectPool<Bullet> pool;

    private void Awake()
    {
        pool = new ObjectPool<Bullet>(bulletPrefab, poolSize, transform);
    }

    public Bullet Fire(Vector3 position, Quaternion rotation)
    {
        Bullet bullet = pool.Get();
        bullet.transform.SetPositionAndRotation(position, rotation);
        bullet.OnFired();
        return bullet;
    }

    public void ReturnBullet(Bullet bullet)
    {
        pool.Release(bullet);
    }
}
```

## 2. Unreal Engine (C++ & Blueprints)

### C++ Class Structure

```cpp
// Weapon.h
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Weapon.generated.h"

UCLASS(BlueprintType, Blueprintable)
class MYGAME_API AWeapon : public AActor
{
    GENERATED_BODY()

public:
    AWeapon();

    // Properties exposed to Blueprint
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weapon")
    float BaseDamage;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weapon")
    float FireRate;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weapon")
    int32 MaxAmmo;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
    USkeletalMeshComponent* Mesh;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
    UArrowComponent* MuzzleFlashLocation;

    // Functions callable from Blueprint
    UFUNCTION(BlueprintCallable, Category = "Weapon")
    void Fire();

    UFUNCTION(BlueprintNativeEvent, Category = "Weapon")
    void OnFireEffects();

    // Delegate
    DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnAmmoChanged, int32, AmmoRemaining);
    UPROPERTY(BlueprintAssignable, Category = "Events")
    FOnAmmoChanged OnAmmoChanged;

protected:
    UPROPERTY(Replicated)
    int32 CurrentAmmo;

    FTimerHandle FireTimerHandle;

    virtual void BeginPlay() override;

    UFUNCTION(Server, Reliable, WithValidation)
    void ServerFire();
};
```

```cpp
// Weapon.cpp
#include "Weapon.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
#include "Kismet/GameplayStatics.h"

AWeapon::AWeapon()
{
    PrimaryActorTick.bCanEverTick = false;
    bReplicates = true;

    Mesh = CreateDefaultSubobject<USkeletalMeshComponent>("Mesh");
    RootComponent = Mesh;

    MuzzleFlashLocation = CreateDefaultSubobject<UArrowComponent>("MuzzleFlash");
    MuzzleFlashLocation->SetupAttachment(Mesh);

    BaseDamage = 25.0f;
    FireRate = 0.2f;
    MaxAmmo = 30;
    CurrentAmmo = MaxAmmo;
}

void AWeapon::BeginPlay()
{
    Super::BeginPlay();
}

void AWeapon::Fire()
{
    if (CurrentAmmo <= 0) return;

    ServerFire();

    if (HasAuthority())
    {
        MulticastFireEffects();
    }

    CurrentAmmo--;
    OnAmmoChanged.Broadcast(CurrentAmmo);

    if (CurrentAmmo <= 0)
    {
        // Reload logic
    }
}

bool AWeapon::ServerFire_Validate()
{
    return true;
}

void AWeapon::ServerFire_Implementation()
{
    // Server-side hit detection
    FHitResult Hit;
    FCollisionQueryParams Params;
    Params.AddIgnoredActor(this);
    Params.AddIgnoredActor(GetOwner());

    FVector Start = MuzzleFlashLocation->GetComponentLocation();
    FVector End = Start + GetOwner()->GetActorForwardVector() * 10000.0f;

    if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
    {
        AActor* HitActor = Hit.GetActor();
        if (HitActor)
        {
            float DamageToApply = BaseDamage * FMath::FRandRange(0.9f, 1.1f);
            UGameplayStatics::ApplyDamage(
                HitActor,
                DamageToApply,
                GetOwner()->GetInstigatorController(),
                this,
                UDamageType::StaticClass()
            );
        }
    }
}

void AWeapon::OnFireEffects_Implementation()
{
    // BlueprintNativeEvent — implement in BP for VFX
}

void AWeapon::MulticastFireEffects_Implementation()
{
    ONFireEffects();
    // Spawn muzzle flash, play sound, etc.
}

void AWeapon::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWeapon, CurrentAmmo);
}
```

### Behavior Tree & AI

```cpp
// BTService_FindEnemy.h
UCLASS()
class MYGAME_API UBTService_FindEnemy : public UBTService
{
    GENERATED_BODY()

public:
    UBTService_FindEnemy();

protected:
    UPROPERTY(EditAnywhere, Category = "AI")
    float SearchRadius = 2000.0f;

    virtual void TickNode(UBehaviorTreeComponent& OwnerComp,
                          uint8* NodeMemory,
                          float DeltaSeconds) override;
};
```

```cpp
// BTService_FindEnemy.cpp
void UBTService_FindEnemy::TickNode(UBehaviorTreeComponent& OwnerComp,
                                    uint8* NodeMemory,
                                    float DeltaSeconds)
{
    Super::TickNode(OwnerComp, NodeMemory, DeltaSeconds);

    AAIController* AIController = OwnerComp.GetAIOwner();
    APawn* AIPawn = AIController->GetPawn();

    if (!AIPawn) return;

    UBlackboardComponent* Blackboard = OwnerComp.GetBlackboardComponent();

    // Find nearest enemy
    TArray<AActor*> FoundActors;
    UGameplayStatics::GetAllActorsOfClass(GetWorld(), APlayerCharacter::StaticClass(), FoundActors);

    AActor* NearestEnemy = nullptr;
    float NearestDist = FLT_MAX;

    for (AActor* Actor : FoundActors)
    {
        float Dist = FVector::Dist(AIPawn->GetActorLocation(), Actor->GetActorLocation());
        if (Dist < SearchRadius && Dist < NearestDist)
        {
            NearestEnemy = Actor;
            NearestDist = Dist;
        }
    }

    Blackboard->SetValueAsObject("Enemy", NearestEnemy);
    Blackboard->SetValueAsBool("HasEnemy", NearestEnemy != nullptr);
}
```

```cpp
// BTTask_Attack.h
UCLASS()
class MYGAME_API UBTTask_Attack : public UBTTaskNode
{
    GENERATED_BODY()

    virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp,
                                            uint8* NodeMemory) override;
};
```

```cpp
// BTTask_Attack.cpp
EBTNodeResult::Type UBTTask_Attack::ExecuteTask(UBehaviorTreeComponent& OwnerComp,
                                                 uint8* NodeMemory)
{
    AAIController* AIController = OwnerComp.GetAIOwner();
    if (!AIController) return EBTNodeResult::Failed;

    APawn* AIPawn = AIController->GetPawn();
    AEnemyCharacter* Enemy = Cast<AEnemyCharacter>(AIPawn);
    if (!Enemy) return EBTNodeResult::Failed;

    Enemy->PerformAttack();

    // Wait for attack animation
    FTimerHandle TimerHandle;
    AIPawn->GetWorldTimerManager().SetTimer(
        TimerHandle,
        FTimerDelegate::CreateLambda([&OwnerComp]()
        {
            OwnerComp.OnTaskFinished(OwnerComp.GetActiveNode(),
                                     EBTNodeResult::Succeeded);
        }),
        1.0f,
        false
    );

    return EBTNodeResult::InProgress;
}
```

### Niagara VFX

```cpp
// Spawning Niagara particle system from C++
UParticleSystemComponent* Particle = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
    GetWorld(),
    ExplosionEffect,
    HitLocation,
    FRotator::ZeroRotator,
    FVector(1.0f),
    true,
    true,
    ENCPoolMethod::AutoRelease
);

// Set parameters
if (Particle)
{
    UNiagaraComponent* NiagaraComp = Cast<UNiagaraComponent>(Particle);
    if (NiagaraComp)
    {
        NiagaraComp->SetFloatParameter("SpawnRate", 100.0f);
        NiagaraComp->SetColorParameter("Color", FLinearColor::Red);
        NiagaraComp->SetVectorParameter("Velocity", FVector(0, 0, 500));
    }
}
```

### Lumen & Nanite

```cpp
// Lumen configuration (in project settings or code)
// Lumen handles real-time global illumination and reflections

// Console commands
// r.Lumen.DiffuseIndirect.Allow 1
// r.Lumen.Reflections.Allow 1
// r.Lumen.ScreenProbeGather 1

// Nanite configuration
// Enable per-mesh via UStaticMesh
UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Meshes/HighDetail"));
if (Mesh)
{
    Mesh->NaniteSettings.bEnabled = true;
    Mesh->NaniteSettings.FallbackPercentTriangles = 0.5f; // Fallback for non-supported
}

// Check Nanite support at runtime
bool bNaniteSupported = GMaxRHIFeatureLevel >= ERHIFeatureLevel::SM6;
```

## 3. Godot (GDScript)

### Node & Scene Structure

```gdscript
# Main player scene structure:
# Player (CharacterBody3D)
# ├── CollisionShape3D
# ├── MeshInstance3D
# ├── AnimationPlayer
# ├── AudioStreamPlayer3D
# └── Camera3D (optional)

extends CharacterBody3D

# Exported variables (editable in inspector)
@export var move_speed: float = 5.0
@export var sprint_multiplier: float = 2.0
@export var jump_velocity: float = 4.5
@export var mouse_sensitivity: float = 0.002

# Internal variables
var current_speed: float
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

# References
@onready var animation_player: AnimationPlayer = $AnimationPlayer
@onready var camera: Camera3D = $Camera3D

func _ready():
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
    current_speed = move_speed

func _input(event):
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        rotate_y(-event.relative.x * mouse_sensitivity)
        camera.rotation.x = clamp(
            camera.rotation.x - event.relative.y * mouse_sensitivity,
            -1.0, 1.0  # In radians, ~57 degrees
        )

func _physics_process(delta):
    # Handle sprint
    if Input.is_action_pressed("sprint"):
        current_speed = move_speed * sprint_multiplier
    else:
        current_speed = move_speed

    # Vertical velocity (gravity & jump)
    if not is_on_floor():
        velocity.y -= gravity * delta

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    # Horizontal movement
    var input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var direction = (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()

    if direction:
        velocity.x = direction.x * current_speed
        velocity.z = direction.z * current_speed
        animation_player.play("Run")
    else:
        velocity.x = move_toward(velocity.x, 0, current_speed)
        velocity.z = move_toward(velocity.z, 0, current_speed)
        animation_player.play("Idle")

    move_and_slide()
```

### Signals (Event System)

```gdscript
# HealthController.gd
extends Node

signal health_changed(current: float, max: float)
signal died()

@export var max_health: float = 100.0
var current_health: float

func _ready():
    current_health = max_health

func take_damage(amount: float):
    current_health = max(0, current_health - amount)
    health_changed.emit(current_health, max_health)

    if current_health <= 0:
        died.emit()

func heal(amount: float):
    current_health = min(max_health, current_health + amount)
    health_changed.emit(current_health, max_health)
```

```gdscript
# UI.gd (connected to health controller)
extends ProgressBar

@export var health_controller: Node

func _ready():
    health_controller.health_changed.connect(_on_health_changed)
    health_controller.died.connect(_on_died)

func _on_health_changed(current: float, max_hp: float):
    value = current / max_hp * 100.0
    modulate = Color(1, current / max_hp, current / max_hp)  # Red as health drops

func _on_died():
    visible = false
    get_tree().change_scene_to_file("res://scenes/game_over.tscn")
```

### State Machine Pattern

```gdscript
# State.gd (base class)
class_name State
extends Node

@warning_ignore("unused_signal")
signal transition(state_name: String)

func enter(_previous_state: String) -> void:
    pass

func exit() -> void:
    pass

func update(_delta: float) -> void:
    pass

func physics_update(_delta: float) -> void:
    pass

func handle_input(_event: InputEvent) -> void:
    pass
```

```gdscript
# PlayerStateMachine.gd
extends Node

@export var initial_state: String = "Idle"

var states: Dictionary = {}
var current_state: State
var current_state_name: String

func _ready():
    # Find all State children
    for child in get_children():
        if child is State:
            states[child.name] = child
            child.transition.connect(_on_transition)

    # Start with initial state
    change_state(initial_state)

func _process(delta):
    if current_state:
        current_state.update(delta)

func _physics_process(delta):
    if current_state:
        current_state.physics_update(delta)

func _input(event):
    if current_state:
        current_state.handle_input(event)

func change_state(new_state: String):
    if current_state:
        current_state.exit()

    current_state = states.get(new_state)
    current_state_name = new_state

    if current_state:
        current_state.enter(current_state_name)

func _on_transition(state_name: String):
    change_state(state_name)
```

```gdscript
# IdleState.gd
extends State

@export var move_speed: float = 5.0

func enter(previous: String):
    print("Entering Idle state from ", previous)

func update(delta):
    if Input.get_vector("left", "right", "forward", "back").length() > 0:
        transition.emit("Moving")
    if Input.is_action_just_pressed("jump"):
        transition.emit("Jumping")

# MovingState.gd
extends State

func enter(previous: String):
    print("Entering Moving state")

func update(delta):
    if Input.get_vector("left", "right", "forward", "back").length() == 0:
        transition.emit("Idle")
    if Input.is_action_just_pressed("jump"):
        transition.emit("Jumping")
    if Input.is_action_just_pressed("attack"):
        transition.emit("Attacking")
```

### A* Pathfinding

```gdscript
# Simple 2D grid A*
class_name Pathfinder

var grid_size: Vector2i
var obstacle_cells: Dictionary = {}

func _init(width: int, height: int):
    grid_size = Vector2i(width, height)

func set_obstacle(cell: Vector2i, is_obstacle: bool):
    if is_obstacle:
        obstacle_cells[cell] = true
    else:
        obstacle_cells.erase(cell)

func find_path(start: Vector2i, end: Vector2i) -> PackedVector2Array:
    var astar_grid = AStar2D.new()
    var point_id = 0
    var id_map = {}

    # Add all walkable cells
    for x in grid_size.x:
        for y in grid_size.y:
            var cell = Vector2i(x, y)
            if not obstacle_cells.has(cell):
                id_map[cell] = point_id
                astar_grid.add_point(point_id, Vector2(cell))

                # Connect to neighbors
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        var neighbor = Vector2i(x + dx, y + dy)
                        if id_map.has(neighbor):
                            var neighbor_id = id_map[neighbor]
                            var weight = 1.0 if dx == 0 or dy == 0 else sqrt(2.0)
                            astar_grid.connect_points(point_id, neighbor_id, false)
                point_id += 1

    # Find path
    var start_id = id_map.get(start)
    var end_id = id_map.get(end)

    if start_id == null or end_id == null:
        return PackedVector2Array()

    var path = astar_grid.get_point_path(start_id, end_id)
    return path
```

## 4. 2D Game Development

### Sprite Rendering Pipeline

```
Scene Setup:
  CanvasLayer (UI)
  WorldEnvironment
  Camera2D
    └── TileMap
    └── Player (Sprite2D)
    └── Enemies (Sprite2D)
    └── Particles2D
    └── ParallaxBackground
```

### Tilemap (Godot)

```gdscript
extends TileMap

# Procedural generation
func generate_dungeon():
    var tiles_used = get_used_cells(0)
    for cell in tiles_used:
        set_cell(0, cell, -1)  # Clear

    var start = Vector2i(5, 5)
    var rooms = generate_rooms(10)
    for room in rooms:
        fill_room(room)

func fill_room(room: Rect2i):
    for x in room.size.x:
        for y in room.size.y:
            var cell = room.position + Vector2i(x, y)
            # Walls on edges
            if x == 0 or y == 0 or x == room.size.x - 1 or y == room.size.y - 1:
                set_cell(0, cell, 0, Vector2i(1, 0))  # Wall
            else:
                set_cell(0, cell, 0, Vector2i(0, 0))  # Floor

func generate_rooms(count: int) -> Array[Rect2i]:
    var rooms: Array[Rect2i] = []
    for i in count:
        var w = randi_range(5, 12)
        var h = randi_range(5, 12)
        var x = randi_range(1, grid_size.x - w - 1)
        var y = randi_range(1, grid_size.y - h - 1)
        rooms.append(Rect2i(x, y, w, h))
    return rooms

# Camera follow with smoothing
extends Camera2D

@export var target: Node2D
@export var smoothing: float = 5.0

func _process(delta):
    if target:
        var target_pos = target.global_position
        global_position = global_position.lerp(target_pos, smoothing * delta)
```

## 5. 3D Game Development

### Rendering Pipeline Comparison

| Feature | Forward Rendering | Deferred Rendering |
|---|---|---|
| MSAA | Yes | Limited |
| Transparency | Easy | Complex |
| Light count | Limited | Many lights |
| Performance | Better with few lights | Better with many lights |
| G-buffer memory | N/A | Higher |

### Shader Examples (Unity)

```hlsl
// Surface shader (PBR)
Shader "Custom/Terrain" {
    Properties {
        _MainTex ("Albedo (RGB)", 2D) = "white" {}
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _HeightMap ("Height Map", 2D) = "gray" {}
        _Tessellation ("Tessellation", Range(1,32)) = 4
    }
    SubShader {
        Tags { "RenderType"="Opaque" }
        LOD 200

        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows tessellate:tess
        #pragma target 5.0

        sampler2D _MainTex;
        sampler2D _NormalMap;
        sampler2D _HeightMap;
        float _Tessellation;

        struct Input {
            float2 uv_MainTex;
            float3 worldPos;
        };

        float4 tess() {
            return _Tessellation;
        }

        void surf (Input IN, inout SurfaceOutputStandard o) {
            fixed4 c = tex2D (_MainTex, IN.uv_MainTex);
            o.Albedo = c.rgb;
            o.Normal = UnpackNormal(tex2D(_NormalMap, IN.uv_MainTex));
            o.Metallic = 0.2;
            o.Smoothness = 0.5;
            o.Alpha = c.a;
        }
        ENDCG
    }
}
```

```glsl
// Godot shader (spatial)
shader_type spatial;

uniform vec2 uv_scale = vec2(1.0);
uniform float wave_speed = 1.0;
uniform float wave_height = 0.1;

void vertex() {
    vec2 world_pos = VERTEX.xz;
    float wave = sin(world_pos.x * 0.5 + TIME * wave_speed) *
                 cos(world_pos.y * 0.3 + TIME * wave_speed * 0.8);
    VERTEX.y += wave * wave_height;

    // Recalculate normal
    vec3 tangent = normalize(vec3(1.0, 0.0, 0.0));
    vec3 bitangent = normalize(cross(tangent, NORMAL));
    TANGENT = tangent;
    BINORMAL = bitangent;
}

void fragment() {
    vec2 uv = UV * uv_scale;
    ALBEDO = texture(ALBEDO_TEXTURE, uv).rgb;
    ROUGHNESS = 0.6;
    METALLIC = 0.1;
}
```

## 6. Spatial Audio

```csharp
// Unity FMOD/Wwise integration (pseudo-code)
// FMOD Studio Event Emitter
[RequireComponent(typeof(StudioEventEmitter))]
public class FootstepAudio : MonoBehaviour
{
    [SerializeField] private StudioEventEmitter footstepEvent;
    [SerializeField] private LayerMask groundLayer;
    private TerrainDetector terrainDetector;

    public void PlayFootstep()
    {
        // Raycast to find surface
        if (Physics.Raycast(transform.position, Vector3.down,
            out RaycastHit hit, 2f, groundLayer))
        {
            string surface = GetSurfaceType(hit);

            // Set FMOD parameter
            footstepEvent.SetParameter("SurfaceType", surface);
            footstepEvent.Play();
        }
    }

    private string GetSurfaceType(RaycastHit hit)
    {
        if (hit.collider.CompareTag("Concrete")) return "concrete";
        if (hit.collider.CompareTag("Grass")) return "grass";
        if (hit.collider.CompareTag("Metal")) return "metal";
        if (hit.collider.CompareTag("Wood")) return "wood";
        return "default";
    }
}
```

```gdscript
# Godot 3D audio
extends AudioStreamPlayer3D

@export var min_distance: float = 1.0
@export var max_distance: float = 20.0
@export var attenuation_model: AudioServer.AttenuationModel = AudioServer.ATTENUATION_INVERSE_SQUARE

func play_at_position(pos: Vector3):
    global_position = pos
    max_distance = max_distance
    attenuation_model = attenuation_model
    play()
```

## 7. AI Systems

### Behavior Trees (Node Structure)

```
Root
└── Selector (try each child until one succeeds)
    ├── Sequence (do all in order)
    │   ├── CheckHealth < 50%
    │   ├── FindHealthPack
    │   └── MoveToHealthPack
    └── Sequence
        ├── FindEnemy
        ├── MoveToEnemy
        └── Selector
            ├── AttackInRange
            └── ChaseEnemy
```

### NavMesh

```csharp
// Unity NavMesh Agent
using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(NavMeshAgent))]
public class AIController : MonoBehaviour
{
    private NavMeshAgent agent;
    private Transform target;

    [SerializeField] private float updateRate = 0.5f;
    [SerializeField] private float stoppingDistance = 2f;
    private float lastUpdateTime;

    private void Awake()
    {
        agent = GetComponent<NavMeshAgent>();
        agent.stoppingDistance = stoppingDistance;
    }

    private void Update()
    {
        if (!target) return;

        // Only recalculate path periodically
        if (Time.time - lastUpdateTime > updateRate)
        {
            agent.SetDestination(target.position);
            lastUpdateTime = Time.time;
        }

        // Dynamic obstacle avoidance
        if (agent.pathStatus == NavMeshPathStatus.PathPartial)
        {
            FindAlternatePath();
        }

        // Animation
        float speed = agent.velocity.magnitude;
        animator.SetFloat("Speed", speed);
    }

    private void FindAlternatePath()
    {
        // Recalculate or find new target
        agent.ResetPath();
        agent.SetDestination(target.position);
    }

    // Sample nearest point on NavMesh
    public bool SamplePosition(Vector3 position, out Vector3 navPosition)
    {
        if (NavMesh.SamplePosition(position, out NavMeshHit hit, 5f, NavMesh.AllAreas))
        {
            navPosition = hit.position;
            return true;
        }
        navPosition = position;
        return false;
    }
}
```

### A* Pathfinding (C#)

```csharp
using System;
using System.Collections.Generic;

public class AStar
{
    public class Node
    {
        public int X, Y;
        public bool Walkable;
        public float G, H;
        public Node Parent;

        public float F => G + H;

        public Node(int x, int y, bool walkable)
        {
            X = x; Y = y;
            Walkable = walkable;
        }
    }

    private Node[,] grid;
    private int width, height;

    public AStar(int width, int height, bool[,] walkableMap)
    {
        this.width = width;
        this.height = height;
        grid = new Node[width, height];

        for (int x = 0; x < width; x++)
            for (int y = 0; y < height; y++)
                grid[x, y] = new Node(x, y, walkableMap[x, y]);
    }

    public List<Node> FindPath(int startX, int startY, int endX, int endY)
    {
        Node start = grid[startX, startY];
        Node end = grid[endX, endY];

        List<Node> open = new List<Node>();
        HashSet<Node> closed = new HashSet<Node>();
        open.Add(start);

        while (open.Count > 0)
        {
            Node current = open[0];
            for (int i = 1; i < open.Count; i++)
            {
                if (open[i].F < current.F || (open[i].F == current.F && open[i].H < current.H))
                    current = open[i];
            }

            open.Remove(current);
            closed.Add(current);

            if (current == end)
                return RetracePath(start, end);

            foreach (Node neighbor in GetNeighbors(current))
            {
                if (!neighbor.Walkable || closed.Contains(neighbor))
                    continue;

                float newG = current.G + GetDistance(current, neighbor);
                if (newG < neighbor.G || !open.Contains(neighbor))
                {
                    neighbor.G = newG;
                    neighbor.H = GetDistance(neighbor, end);
                    neighbor.Parent = current;

                    if (!open.Contains(neighbor))
                        open.Add(neighbor);
                }
            }
        }

        return null; // No path found
    }

    private List<Node> RetracePath(Node start, Node end)
    {
        List<Node> path = new List<Node>();
        Node current = end;

        while (current != start)
        {
            path.Add(current);
            current = current.Parent;
        }
        path.Reverse();
        return path;
    }

    private List<Node> GetNeighbors(Node node)
    {
        List<Node> neighbors = new List<Node>();
        for (int dx = -1; dx <= 1; dx++)
        {
            for (int dy = -1; dy <= 1; dy++)
            {
                if (dx == 0 && dy == 0) continue;

                int nx = node.X + dx;
                int ny = node.Y + dy;

                if (nx >= 0 && nx < width && ny >= 0 && ny < height)
                    neighbors.Add(grid[nx, ny]);
            }
        }
        return neighbors;
    }

    private float GetDistance(Node a, Node b)
    {
        float dx = Math.Abs(a.X - b.X);
        float dy = Math.Abs(a.Y - b.Y);
        return dx > dy ? 14 * dy + 10 * (dx - dy) : 14 * dx + 10 * (dy - dx);
    }
}
```

## 8. Performance Optimization

| Technique | Tool | Impact |
|---|---|---|
| Object pooling | Custom pool | Reduces allocation spikes |
| LOD (Level of Detail) | Unity LOD Group | Fewer triangles at distance |
| Occlusion culling | Unity Occlusion Culling | Skip rendering hidden objects |
| GPU instancing | Same material meshes | Single draw call for many objects |
| Texture atlas | Sprite packing | Fewer material switches |
| Batching (static/dynamic) | Unity static batching | Combine meshes |
| Animation culling | Animator.cullingMode | Stop animating far objects |
| Lightmap baking | Progressive Lightmapper | No real-time shadow calculations |
| Level streaming | Scene loading/unloading | Memory management |
| Profiler | Unity Profiler, Unreal Insights | Identify bottlenecks |

```csharp
// LOD Group setup in code
public class LODSetup : MonoBehaviour
{
    public void ConfigureLOD(Mesh high, Mesh medium, Mesh low)
    {
        LODGroup group = gameObject.AddComponent<LODGroup>();
        LOD[] lods = new LOD[3];

        Renderer renderer = GetComponent<Renderer>();
        renderer.sharedMesh = high;

        lods[0] = new LOD(0.3f, new Renderer[] { CreateLODRenderer(high, renderer) });
        lods[1] = new LOD(0.15f, new Renderer[] { CreateLODRenderer(medium, renderer) });
        lods[2] = new LOD(0.05f, new Renderer[] { CreateLODRenderer(low, renderer) });

        group.SetLODs(lods);
    }

    private Renderer CreateLODRenderer(Mesh mesh, Renderer template)
    {
        GameObject go = new GameObject("LOD");
        go.transform.SetParent(transform);
        var mr = go.AddComponent<MeshRenderer>();
        var mf = go.AddComponent<MeshFilter>();
        mr.sharedMaterial = template.sharedMaterial;
        mf.sharedMesh = mesh;
        return mr;
    }
}
```
