import { useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { FolderOpen, CheckCircle2, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function VaultConfig() {
  const [vaultPath, setVaultPath] = useState('/path/to/obsidian/vault')
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState<'idle' | 'success' | 'error'>('idle')

  const handleSync = async () => {
    setIsSyncing(true)
    setSyncStatus('idle')

    // Simulate sync operation
    setTimeout(() => {
      setIsSyncing(false)
      setSyncStatus('success')

      // Reset status after 3 seconds
      setTimeout(() => setSyncStatus('idle'), 3000)
    }, 2000)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FolderOpen className="h-5 w-5" />
          Vault Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="vault-path">Obsidian Vault Path</Label>
          <div className="flex gap-2">
            <Input
              id="vault-path"
              value={vaultPath}
              onChange={(e) => setVaultPath(e.target.value)}
              placeholder="/path/to/obsidian/vault"
              className="flex-1"
            />
            <Button onClick={handleSync} disabled={isSyncing}>
              {isSyncing ? 'Syncing...' : 'Sync'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Path to your Obsidian vault directory for indexing
          </p>
        </div>

        {syncStatus === 'success' && (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              Vault synced successfully! Index is up to date.
            </AlertDescription>
          </Alert>
        )}

        {syncStatus === 'error' && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to sync vault. Please check the path and try again.
            </AlertDescription>
          </Alert>
        )}

        <div className="pt-4 border-t space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total Documents:</span>
            <span className="font-medium">1,234</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Last Indexed:</span>
            <span className="font-medium">2 hours ago</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Index Size:</span>
            <span className="font-medium">45.2 MB</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
