"""
Script de diagnostic et correction des paramètres SSM manquants pour le Lab 2.
Valeurs par défaut tirées du template CloudFormation (cfn.yaml).
"""
import boto3

REGION = "us-west-2"

# Valeurs par défaut du cfn.yaml
DEFAULTS = {
    "prod_search_agent_model_id":        "anthropic.claude-3-haiku-20240307-v1:0",
    "anycomp_prod_reviews_mcp_server_url": "NOT CONFIGURED",
    "anycomp_agcore_gw_cognito_accesstoken": "placeholder-cognito-access-token",
    # product_search_kb_id est géré par l'EC2 UserData — ne pas écraser
}

ssm = boto3.client("ssm", region_name=REGION)

PARAMS = [
    "product_search_kb_id",
    "prod_search_agent_model_id",
    "anycomp_prod_reviews_mcp_server_url",
    "anycomp_agcore_gw_cognito_accesstoken",
]

print(f"=== Vérification des paramètres SSM dans {REGION} ===\n")

for name in PARAMS:
    try:
        val = ssm.get_parameter(Name=name)["Parameter"]["Value"]
        print(f"  ✅ {name} = {val[:80]}{'...' if len(val) > 80 else ''}")
    except ssm.exceptions.ParameterNotFound:
        if name in DEFAULTS:
            default = DEFAULTS[name]
            print(f"  ❌ {name} MANQUANT — création avec valeur par défaut: {default}")
            ssm.put_parameter(
                Name=name,
                Value=default,
                Type="String",
                Description=f"Recréé par fix_ssm_params.py (valeur CFN par défaut)",
                Overwrite=True,
            )
            print(f"  ✅ {name} créé.")
        else:
            print(f"  ❌ {name} MANQUANT — ce paramètre est créé par l'EC2 UserData du CFN.")
            print(f"     → Vérifiez que le stack CloudFormation a bien été déployé et que l'EC2 a terminé son initialisation.")
    except Exception as e:
        print(f"  ⚠️  {name} — erreur: {e}")

print("\n=== Terminé ===")
print("\nNote importante :")
print("  • prod_search_agent_model_id  → modèle Bedrock utilisé par l'agent")
print("  • anycomp_prod_reviews_mcp_server_url → à mettre à jour avec l'URL de votre AgentCore Gateway")
print("    Valeur visible dans le commentaire du script principal :")
print("    https://gateway-pd-search-3i6jwil1zz.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp")
print("  • anycomp_agcore_gw_cognito_accesstoken → token Cognito généré par la Lambda CognitoSetup du CFN")