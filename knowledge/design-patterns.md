# Software Design Patterns Reference

## Creational Patterns
- **Singleton**: One instance globally. Use for caches, configs, logging.
- **Factory Method**: Create objects without specifying exact class.
- **Abstract Factory**: Families of related objects.
- **Builder**: Complex object construction step-by-step.
- **Prototype**: Clone existing objects.

## Structural Patterns
- **Adapter**: Make incompatible interfaces work together.
- **Bridge**: Separate abstraction from implementation.
- **Composite**: Tree structures of objects (UI components).
- **Decorator**: Add responsibilities dynamically.
- **Facade**: Simplified interface to complex subsystem.
- **Flyweight**: Share fine-grained objects.
- **Proxy**: Surrogate/placeholder for another object.

## Behavioral Patterns
- **Chain of Responsibility**: Pass request along handler chain.
- **Command**: Encapsulate request as object.
- **Interpreter**: Grammar interpretation.
- **Iterator**: Sequential access to elements.
- **Mediator**: Centralized communication between objects.
- **Memento**: Capture/restore object state.
- **Observer**: One-to-many dependency notification.
- **State**: Alter behavior when state changes.
- **Strategy**: Interchangeable algorithms.
- **Template Method**: Algorithm skeleton, subclasses fill steps.
- **Visitor**: New operations without changing classes.

## Modern / Architectural Patterns
- **MVVM**: Model-View-ViewModel (WPF, SwiftUI, Compose)
- **MVC**: Model-View-Controller (web frameworks)
- **Clean Architecture**: Dependency inversion, use cases
- **Hexagonal Architecture**: Ports and adapters
- **CQRS**: Separate read/write models
- **Event Sourcing**: State = sequence of events
- **Saga**: Distributed transaction management
- **Strangler Fig**: Incrementally replace legacy systems
