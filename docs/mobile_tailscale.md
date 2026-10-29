# Jarvis sur téléphone via Tailscale

Utiliser le vrai Jarvis (celui du PC Windows) depuis un téléphone ou une
tablette, de n'importe où, **sans exposer le HUD ni ouvrir de port sur
Internet**. Le téléphone est un *satellite* : il envoie la voix, le PC fait tout
le travail (Whisper, LLM, outils, TTS) et renvoie la réponse parlée.

Le HUD (`127.0.0.1:8770`), le panneau et le cockpit restent **strictement
locaux** ; rien de leur garde n'est assoupli. Seule la page `/mobile` est servie,
par le listener satellite dédié (`8792`, TLS), jamais par le serveur unifié ni
derrière ngrok.

## Droits à distance

Un client qui arrive par Tailscale est « hors maison » :

- N1 : direct ; N2 : confirmation vocale ;
- **N3 (mail, appel, réservation, suppression, extinction…) : refusé**, quel que
  soit le réglage.
- Micro de la maison, caméra et domotique ne sont pas exposés : seule la voix du
  téléphone est traitée.

## Installation (une fois)

1. **Tailscale** sur le PC et sur le téléphone, même compte. Dans la console
   d'administration Tailscale (login.tailscale.com), activer **MagicDNS** et
   **HTTPS Certificates**.
2. **Certificat HTTPS valide** (le micro d'un navigateur mobile l'exige). Sur le
   PC, dans un dossier hors dépôt (par exemple `C:\Users\<vous>\jarvis-certs`) :
   ```powershell
   tailscale cert mon-pc.mon-tailnet.ts.net
   ```
   Le nom exact est visible dans `tailscale status` ou la console. Les fichiers
   `.crt` et `.key` sont créés dans le dossier courant. **Ne jamais les
   versionner** ; la clé reste privée. Le certificat dure environ 90 jours :
   relancer la commande pour le renouveler.
3. **`config.yaml`** (privé) :
   ```yaml
   satellites:
     - id: "telephone"
       piece: "salon"
       token: "<chaîne aléatoire longue>"
       actions_critiques: false

   satellite_lan:
     certificat_tailscale: "C:/Users/<vous>/jarvis-certs/mon-pc.mon-tailnet.ts.net.crt"
     cle_tailscale: "C:/Users/<vous>/jarvis-certs/mon-pc.mon-tailnet.ts.net.key"
     clair: false          # ferme le port 8791 en clair
   ```
   Générer le token : `python -c "import secrets;print(secrets.token_urlsafe(24))"`.
   Chaque appareil a son propre `id` et son propre token.
4. **Pare-feu Windows** : autoriser le port TCP **8792** uniquement depuis
   l'interface Tailscale (plage `100.64.0.0/10`), pas depuis le Wi-Fi public.
5. Redémarrer Jarvis (`uv run python jarvis14.py`).

## Utilisation

Sur le téléphone, avec Tailscale actif, ouvrir :

```
https://mon-pc.mon-tailnet.ts.net:8792/mobile
```

Saisir l'identifiant et le token, se connecter, puis toucher le micro pour
parler et le retoucher pour envoyer. La réponse est lue à voix haute. « Retenir
sur cet appareil » stocke l'identifiant et le token dans le navigateur de ce
téléphone seulement : ne cochez pas sur un appareil partagé.

## Dépannage

- **Page inaccessible** : Tailscale actif sur les deux appareils ? pare-feu 8792 ?
  Jarvis démarré avec au moins un satellite configuré (sinon le listener ne
  s'ouvre pas) ?
- **Avertissement de certificat** : le certificat Tailscale n'est pas chargé
  (chemins faux, fichiers absents) ; Jarvis se replie alors sur l'auto-signé, que
  les navigateurs mobiles refusent pour le micro. Voir le journal
  (`tls_lan: certificat Tailscale introuvable`).
- **« satellite inconnu ou token invalide »** : `id`/`token` différents de
  `config.yaml`.
- **Micro refusé** : autoriser le micro pour le site dans les réglages du
  navigateur.
- **Pas de son sur iPhone** : le mode silencieux coupe la sortie web audio ; le
  son démarre après le premier toucher du bouton.

## Ce qui n'est pas validé

Le code est testé (route `/mobile`, choix du certificat, garde réseau), mais ni le
micro du téléphone, ni la lecture audio, ni la chaîne Tailscale réelle n'ont pu
être vérifiés automatiquement : à valider sur votre matériel.
