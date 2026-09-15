from chat.chat_service import ChatService


def main():
    service = ChatService()

    print("=" * 70)
    print("Terraform AI Module Generator")
    print("=" * 70)

    request = input(
        "\nWhat infrastructure do you want to create?\n> "
    ).strip()

    if not request:
        print("No request supplied.")
        return

    try:
        result = service.process(request)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        return

    print("\nPLAN")
    print("-" * 70)
    print(result["plan"])

    print("\nRECOMMENDED MODULES")
    print("-" * 70)

    for module in result["recommended_modules"]:
        print(
            f"{module['module']} "
            f"(score={module['score']})"
        )
        if module.get("reasons"):
            print(
                f"  reasons: {', '.join(module['reasons'])}"
            )

    print("\nSELECTED MODULES")
    print("-" * 70)

    for module in result["selected_modules"]:
        print(
            f"{module['module']} "
            f"[{module['selection_type']}]"
        )

    print("\nDEPLOYMENT ORDER")
    print("-" * 70)

    for module in result["deployment_order"]:
        print(module)


if __name__ == "__main__":
    main()
