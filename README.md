<div align="center">
  <img src="https://avatars.githubusercontent.com/u/2739187?s=280&v=4" alt="GNS3 Logo" width="100px" />
</div>

<p align="center">Projet GNS - 3TC Groupe 33</p>

<div align="center">
  <img alt="Python 3" src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54">
  <img alt="Telnet" src="https://img.shields.io/badge/Telnet-grey?style=for-the-badge">
  <img alt="GNS3" src="https://img.shields.io/badge/GNS-v3-7340be?style=for-the-badge">
  <img alt="Cisco" src="https://img.shields.io/badge/cisco_router-%23049fd9.svg?style=for-the-badge&logo=cisco&logoColor=%23ffffff">

</div>

# Sommaire

- [Objectif du projet](#objectif-du-projet)
- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Usage](#usage)
- [Fichier d'intention](#fichier-dintention)

# Objectif du projet

Le but du projet GNS 3 est de développer un outil, dans notre cas en python, capable de configurer automatiquement des routeurs cisco dans le logiciel GNS3.

Notre outil permet de créer rapidement et de façon fiable des réseaux complexes comprenant plusieurs AS avec des relations client-fournisseur ou peer-to-peer, tout en étant en gardant une grande flexibilité.

Concrètement, la configuration du réseau est décrite de façon déléclarative dans un fichier d'intention en json et notre programme traduit cela en commandes impératives rentrées automatiquement dans les routeurs.

# Fonctionnalités

- État du réseau décrit dans un fichier d'intention
- Envoie automatique des commandes vers les routeurs via Telnet
- Création dans GNS3 du projet, des routeurs et de leurs liens
- Récupération des port Telnet des routeurs dans GNS ou configuration manuelle
- Adresses IP choisies automatiquement  ou parmis un pool
- Nombre illimité d'AS, de routeurs et de liens
- eBGP & iBGP
- RIP ou OSPF en protocole de routage au sein d'une AS
- OPSF Metrics
- Relations entre les AS (client-fournisseur, peer-to-peer) grâce aux communty policies

# Installation

### Prérequis

- Python 3
- Pip
- GNS3
- Image du routeur Cisco 7200 avec n interfaces PA-GE installées dans les slots

### Dépendances

Il est recommandé d'utiliser un environnement virtuel python pour l'installation des [dépendances](https://github.com/leopoldcst/GNS/blob/main/requirements.txt).

- gns3fy
- telnetlib3
- rich
- click

### Téléchargement
```bash
git clone https://github.com/leopoldcst/GNS.git
cd GNS
```

### Venv et dépendances
```bash
# Unix (MacOs/Linux) & Windows
python3 -m venv venv/
source ./venv/bin/activate

# Windows
python3 -m venv venv/ # or -> py -m venv venv\
.\venv\Scripts\activate

pip3 install -r ./requirements.txt
```



<details>
<summary>Ou avec uv</summary>

```bash
uv init
uv add -r requirements.txt  
```

</details>
<br/>

# Usage

En l’absence de paramètres, le script choisit le fichier d'intention d'exemple : `intents/intent_2_AS_OSPF_RIP.json`.

Il est possible de préciser le chemin vers le fichier d'intention en fin de commande

```bash
# Syntaxe
python main.py <intent_file_path>

# Exemple
python main.py intents/intent_2_AS_OSPF.json
```

<details>
<summary>Ou avec uv</summary>

```bash
# Syntaxe
uv run main.py <intent_file_path>

# Exemple
uv run main.py intents/intent_2_AS_OSPF.json
```

</details>
<br/>

# Fichier d'intention

Sauf précisé, toutes les propriétés sont obligatoires.

## Structure Principale (Racine)

Ce tableau décrit les clés de haut niveau présentes à la racine du fichier JSON.

| Nom propriété | Type | Description |
| - | - | - |
| [gns_auto_config](#gns_auto_config) | object | Configuration globale pour l'automatisation GNS3 |
| [as](#as) | array | Liste des systèmes autonomes et de leurs protocoles |
| [routers](#routers) | array | Inventaire des routeurs du réseau |
| [links](#links) | array | Topologie physique (câblage) |
| [address_pool](#address_pool) | object | (Optionnel) Pools d'adresses IP manuelles (si la génération auto est désactivée) |
| [client_provider_relationships](#client_provider_relationships) | array | (Optionnel) Définition des relations BGP Client / Fournisseur |
| [peer_to_peer_relationships](#peer_to_peer_relationships) | array | (Optionnel) Définition des relations BGP de Peering |
| [community_constants](#community_constants) | object | Optionnel (Requis si relations BGP utilisées) Configuration des tags et préférences locales pour BGP | 
| write | boolean | (Optionnel) Sauvegarde la config sur tous les routeurs |

## gns_auto_config

| Nom propriété | Type | Description | Valeur par défaut / Exemple |
| - | - | - | - |
| enable | boolean | (Optionnel) Active la connexion au serveur GNS | `false` |
| host | string | (Optionnel) Adresse IP du serveur GNS | `"127.0.0.1"` |
| port | string | (Optionnel) Port d'écoute du serveur GNS | `"3080"` |
| project_name | string | (Obligatoire si enable=true) Nom du projet dans GNS3 | (ex: `"Test_Project"`) |
| create_routers | boolean | (Optionnel) Création automatique des nœuds routeurs dans le projet | `false` |
| create_links | boolean | (Optionnel) Création automatique des liens physiques entre routeurs | `false` |
| arrange_automagically | (Optionnel) boolean | Tente d'organiser visuellement les nœuds automatiquement en groupant par AS | `false` |
| auto_fetch_router_infos | boolean | (Optionnel) Récupère automatiquement les IDs et ports des routeurs via l'API | `false` |
| auto_create_address | object | (Optionnel) Configuration de la génération automatique d'IP (voir tableau suivant) | `{ "physical": true, "Loopback": true }` |

### auto_create_address (Sous-objet de gns_auto_config)

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| physical | boolean | (Optionnel) Si `true`, génère automatiquement les IPs des liens physiques. Si `false`, utilise `address_pool`. | `true` |
| Loopback | boolean | (Optionnel) Si `true`, génère automatiquement les IPs des Loopbacks. Si `false`, utilise `address_pool`. | `false` |

## as

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| asn | integer | Numéro de l'AS | `1` |
| internal_protocol | string | Protocole de routage interne utilisé (IGP) | `"OSPF"` ou `"RIP"` |

## routers

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| name | string | Nom d'hôte (hostname) du routeur | `"R1"` |
| asn | integer | Numéro d'AS auquel appartient ce routeur | `1` |
| host | string | (Optionnel si create_routers=true et auto_fetch_router_infos=true) Adresse ip du routeur | `"127.0.0.1"` |
| port | string | (Optionnel si create_routers=true et auto_fetch_router_infos=true) Port Telent du routeur | `"5001"` |
| write | boolean | (Optionnel) Sauvegarde la config | `true` |

## links

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| from | string | Nom du routeur source | `"R1"` |
| to | string | Nom du routeur destination | `"R2"` |
| interface_from | string | Interface de départ sur le routeur source | `"g1/0"` |
| interface_to | string | Interface d'arrivée sur le routeur destination | `"g1/0"` |
| ospf_cost | object | (Optionnel même en protocole OPSF) Surcharge le coût OSPF par défaut (voir tableau suivant) | `{ "from": 10, "to": 10 }` |

### ospf_cost (Sous-objet de links)

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| from | integer | Coût OSPF configuré sur l'interface du routeur source | `10` |
| to | integer | Coût OSPF configuré sur l'interface du routeur destination | `10` |

## address_pool

*Ce tableau est utilisé uniquement si `auto_create_address` est défini sur `false`.*

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| physical | array | Liste de tableaux contenant les paires d'IP pour les liens point-à-point | `[["fd1::1/64", "fd1::2/64"], ...]` |
| Loopback | array | Liste de chaînes de caractères pour les IPs des interfaces Loopback | `["fd3a::1/128", ...]` |

## client_provider_relationships

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| client | integer | ASN du client | `1` |
| provider | integer | ASN du fournisseur | `2` |

## peer_to_peer_relationships

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| peer_1 | integer | ASN du premier pair | `3` |
| peer_2 | integer | ASN du second pair | `6` |

## community_constants

*Cet objet définit les paramètres pour les clés : `client`, `provider`, et `peer`.*

| Nom propriété | Type | Description | Exemple |
| - | - | - | - |
| value_suffix | integer | Suffixe numérique pour la valeur de la communauté BGP | `42` |
| route_map_tag | string | Tag utilisé pour marquer les routes dans les Route-Maps | `"TAG_PROVIDER"` |
| community_list_name | string | Nom de la liste de communauté | `"PROVIDER"` |
| local_pref | integer | Valeur de la "Local Preference" à appliquer | `300` |